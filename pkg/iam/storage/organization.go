package storage

import (
    "fmt"
    "database/sql"
    "strings"

    "github.com/gosimple/slug"
    "github.com/go-sql-driver/mysql"
    "github.com/golang/protobuf/proto"

    "github.com/jaypipes/procession/pkg/util"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    pb "github.com/jaypipes/procession/proto"
)

// Simple wrapper struct that allows us to pass the internal ID for an
// orgranization around with a protobuf message of the external representation
// of the organization
type OrganizationWithId struct {
    pb *pb.Organization
    id int64
    rootOrgId int64
}

// Returns a sql.Rows yielding organizations matching a set of supplied filters
func (s *Storage) OrganizationList(
    filters *pb.OrganizationListFilters,
) (storage.RowIterator, error) {
    defer s.log.WithSection("iam/storage")()

    numWhere := 0
    if filters.Uuids != nil {
        numWhere = numWhere + len(filters.Uuids)
    }
    if filters.DisplayNames != nil {
        numWhere = numWhere + len(filters.DisplayNames)
    }
    if filters.Slugs != nil {
        numWhere = numWhere + len(filters.Slugs)
    }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    qs := `
SELECT
  o.uuid
, o.display_name
, o.slug
, o.generation
, po.uuid as parent_uuid
FROM organizations AS o
LEFT JOIN organizations AS po
  ON o.parent_organization_id = po.id
`
    if numWhere > 0 {
        qs = qs + "WHERE "
        if filters.Uuids != nil {
            qs = qs + fmt.Sprintf(
                "o.uuid %s",
                sqlutil.InParamString(len(filters.Uuids)),
            )
            for _,  val := range filters.Uuids {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.DisplayNames != nil {
            if qidx > 0{
                qs = qs + "\n AND "
            }
            qs = qs + fmt.Sprintf(
                "o.display_name %s",
                sqlutil.InParamString(len(filters.DisplayNames)),
            )
            for _,  val := range filters.DisplayNames {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.Slugs != nil {
            if qidx > 0 {
                qs = qs + "\n AND "
            }
            qs = qs + fmt.Sprintf(
                "o.slug %s",
                sqlutil.InParamString(len(filters.Slugs)),
            )
            for _,  val := range filters.Slugs {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
    }

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Deletes an organization, all organization members and child organizations,
// and any resources the organization owns
func (s *Storage) OrganizationDelete(
    sess *pb.Session,
    search string,
) error {
    defer s.log.WithSection("iam/storage")()

    // First, we find the target organization's internal ID, parent ID (if any)
    // and the parent's generation value
    var orgId uint64
    var orgUuid string
    var orgDisplayName string
    var orgSlug string
    var rootOrgId uint64
    var nsLeft uint64
    var nsRight uint64
    var orgGeneration uint32
    var parentUuid sql.NullString
    var parentId sql.NullInt64
    var parentGeneration sql.NullInt64
    qargs := make([]interface{}, 0)

    qs := `
SELECT
  o.id
, o.uuid
, o.display_name
, o.slug
, o.root_organization_id
, o.nested_set_left
, o.nested_set_right
, o.generation
, po.id
, po.uuid
, po.generation
FROM organizations AS o
LEFT JOIN organizations AS po
 ON o.parent_organization_id
WHERE `
    if util.IsUuidLike(search) {
        qs = qs + "o.uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "o.display_name = ? OR o.slug = ?"
        qargs = append(qargs, search)
        qargs = append(qargs, search)
    }

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return err
    }
    err = rows.Err()
    if err != nil {
        return err
    }
    defer rows.Close()
    for rows.Next() {
        err = rows.Scan(
            &orgId,
            &orgUuid,
            &orgDisplayName,
            &orgSlug,
            &rootOrgId,
            &nsLeft,
            &nsRight,
            &orgGeneration,
            &parentId,
            &parentUuid,
            &parentGeneration,
        )
        if err != nil {
            return err
        }
        break
    }

    if orgId == 0 {
        notFound := fmt.Errorf("No such organization found.")
        return notFound
    }

    before := &pb.Organization{
        Uuid: orgUuid,
        DisplayName: orgDisplayName,
        Slug: orgSlug,
        Generation: orgGeneration,
    }
    if parentUuid.Valid {
        before.ParentUuid = &pb.StringValue{Value: parentUuid.String}
    }

    msg := "Deleting organization %d (left: %d, right %d)"
    s.log.L2(msg, orgId, nsLeft, nsRight)

    tx, err := s.db.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()

    treeOrgIds := s.orgIdsFromParentId(orgId)

    // First delete all user memberships from the tree's organizations
    qs = `
DELETE FROM organization_users
WHERE organization_id ` + sqlutil.InParamString(len(treeOrgIds)) + `
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    res, err := stmt.Exec(treeOrgIds...)
    if err != nil {
        return err
    }

    // Next delete all the organization records themselves
    qs = `
DELETE FROM organizations
WHERE id ` + sqlutil.InParamString(len(treeOrgIds)) + `
`

    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    res, err = stmt.Exec(treeOrgIds...)
    if err != nil {
        return err
    }

    // Finally, if the deleted organization was a child organization,
    // recalculate the nested set boundaries for the parent
    if parentId.Valid {
        childWidth := nsRight - nsLeft + 1
        qs = `
UPDATE organizations
SET nested_set_left = nested_set_left - ?
WHERE nested_set_left > ?
AND root_organization_id = ?
`

        s.log.SQL(qs)

        stmt, err = tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        res, err = stmt.Exec(childWidth, nsRight, rootOrgId)
        if err != nil {
            return err
        }
        qs = `
UPDATE organizations
SET nested_set_right = nested_set_right - ?
WHERE nested_set_right > ?
AND root_organization_id = ?
`

        s.log.SQL(qs)

        stmt, err = tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        res, err = stmt.Exec(childWidth, nsRight, rootOrgId)
        if err != nil {
            return err
        }
        // Ensure the parent generation hasn't changed (and thus the nested set
        // modeling of the org) since we started changing the org tree for the
        // deleted node
        qs = `
UPDATE organizations
SET generation = generation + 1
WHERE id = ?
AND generation = ?
`

        s.log.SQL(qs)

        stmt, err = tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        res, err = stmt.Exec(
            uint64(parentId.Int64),
            uint64(parentGeneration.Int64),
        )
        if err != nil {
            return err
        }
        na, err := res.RowsAffected()
        if err != nil {
            return err
        }
        if na != 1 {
            err = fmt.Errorf("Concurrent update of parent organization " +
                             "occurred while deleting child.")
            return err
        }
    }
    err = tx.Commit()
    if err != nil {
        return err
    }
    // Write an event log entry for the deletion
    b, err := proto.Marshal(before)
    if err != nil {
        return err
    }
    err = s.events.Write(
        sess,
        pb.EventType_DELETE,
        pb.ObjectType_ORGANIZATION,
        orgUuid,
        b,
        nil,
    )
    if err != nil {
        return err
    }
    return nil
}

// Returns a pb.Organization record filled with information about a requested
// organization.
func (s *Storage) OrganizationGet(
    search string,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/storage")()

    qargs := make([]interface{}, 0)
    qs := `
SELECT
  o.uuid
, o.display_name
, o.slug
, o.generation
, po.uuid as parent_uuid
FROM organizations AS o
LEFT JOIN organizations AS po
  ON o.parent_organization_id = po.id
WHERE `
    if util.IsUuidLike(search) {
        qs = qs + "o.uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "o.display_name = ? OR o.slug = ?"
        qargs = append(qargs, search)
        qargs = append(qargs, search)
    }

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    org := pb.Organization{}
    for rows.Next() {
        var parentUuid sql.NullString
        err = rows.Scan(
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &parentUuid,
        )
        if err != nil {
            return nil, err
        }
        if parentUuid.Valid {
            sv := &pb.StringValue{Value: parentUuid.String}
            org.ParentUuid = sv
        }
        break
    }
    return &org, nil
}

// Given an identifier (slug or UUID), return the organization's internal
// integer ID. Returns 0 if the organization could not be found.
func (s *Storage) orgIdFromIdentifier(identifier string) int64 {
    defer s.log.WithSection("iam/storage")()

    qargs := make([]interface{}, 0)
    qs := `
SELECT id FROM
organizations
WHERE `
    qs = orgBuildWhere(qs, identifier, &qargs)

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return 0
    }
    err = rows.Err()
    if err != nil {
        return 0
    }
    defer rows.Close()
    var output int64
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return 0
        }
        break
    }
    return output
}

// Given an identifier (slug or UUID), return the organization's root
// integer ID. Returns 0 if the organization could not be found.
func (s *Storage) rootOrgIdFromIdentifier(identifier string) uint64 {
    defer s.log.WithSection("iam/storage")()

    qargs := make([]interface{}, 0)
    qs := `
SELECT root_organization_id
FROM organizations
WHERE `
    qs = orgBuildWhere(qs, identifier, &qargs)

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return 0
    }
    err = rows.Err()
    if err != nil {
        return 0
    }
    defer rows.Close()
    output := uint64(0)
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return 0
        }
        break
    }
    return output
}

// Given an internal organization ID of a parent organization, return a slice
// of integers representing the internal organization IDs of the entire subtree
// under the parent, including the parent organization ID.
func (s *Storage) orgIdsFromParentId(
    parentId uint64,
) []interface{} {
    defer s.log.WithSection("iam/storage")()

    qs := `
SELECT o1.id
FROM organizations AS o1
JOIN organizations AS o2
ON o1.root_organization_id = o2.root_organization_id
AND o1.nested_set_left BETWEEN o2.nested_set_left AND o2.nested_set_right
WHERE o2.id = ?
`
    s.log.SQL(qs)

    rows, err := s.db.Query(qs, parentId)
    if err != nil {
        return nil
    }
    err = rows.Err()
    if err != nil {
        return nil
    }
    defer rows.Close()
    output := make([]interface{}, 0)
    for rows.Next() {
        x := 0
        err = rows.Scan(&x)
        if err != nil {
            return nil
        }
        output = append(output, x)
    }
    return output
}

// Returns the integer ID of an organization given its UUID. Returns -1 if an
// organization with the UUID was not found
func (s *Storage) orgIdFromUuid(
    uuid string,
) int {
    defer s.log.WithSection("iam/storage")()

    qs := `
SELECT id
FROM organizations
WHERE uuid = ?
`

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, uuid)
    if err != nil {
        return -1
    }
    err = rows.Err()
    if err != nil {
        return -1
    }
    defer rows.Close()
    orgId := -1
    for rows.Next() {
        err = rows.Scan(&orgId)
        if err != nil {
            return -1
        }
    }
    return orgId
}

// Builds the WHERE clause for single organization search by identifier
func orgBuildWhere(
    qs string,
    search string,
    qargs *[]interface{},
) string {
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        *qargs = append(*qargs, util.UuidFormatDb(search))
    } else {
        qs = qs + "display_name = ? OR slug = ?"
        *qargs = append(*qargs, search)
        *qargs = append(*qargs, search)
    }
    return qs
}

// Given a name, slug or UUID, returns that organization or an error if the
// organization could not be found
func (s *Storage) orgFromIdentifier(
    identifier string,
) (*OrganizationWithId, error) {
    defer s.log.WithSection("iam/storage")()

    qargs := make([]interface{}, 0)
    qs := `
SELECT
  o.id
, o.uuid
, o.display_name
, o.slug
, o.generation
, o.root_organization_id
, po.uuid AS parent_organization_uuid
FROM organizations AS o
LEFT JOIN organizations AS po
  ON o.parent_organization_id = po.id
WHERE `
    if util.IsUuidLike(identifier) {
        qs = qs + "o.uuid = ?"
        qargs = append(qargs, util.UuidFormatDb(identifier))
    } else {
        qs = qs + "o.display_name = ? OR o.slug = ?"
        qargs = append(qargs, identifier)
        qargs = append(qargs, identifier)
    }

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    org := &pb.Organization{}
    orgWithId := &OrganizationWithId{
        pb: org,
    }
    for rows.Next() {
        var parentUuid sql.NullString
        err = rows.Scan(
            &orgWithId.id,
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &orgWithId.rootOrgId,
            &parentUuid,
        )
        if err != nil {
            return nil, err
        }
        if parentUuid.Valid {
            org.ParentUuid = &pb.StringValue{
                Value: parentUuid.String,
            }
        }
    }
    return orgWithId, nil
}

// Given an integer parent org ID, returns that parent's root organization or
// an error if the root organization could not be found
func (s *Storage) rootOrgFromParent(
    parentId int64,
) (*OrganizationWithId, error) {
    defer s.log.WithSection("iam/storage")()

    qs := `
SELECT
  ro.id
, ro.uuid
, ro.display_name
, ro.slug
, ro.generation
FROM organizations AS po
JOIN organizations AS ro
  ON po.root_organization_id = ro.id
WHERE po.id = ?
`

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, parentId)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    var rootId int64
    org := &pb.Organization{}
    for rows.Next() {
        err = rows.Scan(
            &rootId,
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
        )
        if err != nil {
            return nil, err
        }
    }
    return &OrganizationWithId{
        pb: org,
        id: rootId,
    }, nil
}

// Adds a new top-level organization record
func (s *Storage) orgNewRoot(
    sess *pb.Session,
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/storage")()

    tx, err := s.db.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)

    qs := `
INSERT INTO organizations (
  uuid
, display_name
, slug
, generation
, root_organization_id
, parent_organization_id
, nested_set_left
, nested_set_right
) VALUES (?, ?, ?, ?, NULL, NULL, 1, 2)
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    res, err := stmt.Exec(
        uuid,
        displayName,
        slug,
        1,
    )
    if err != nil {
        me, ok := err.(*mysql.MySQLError)
        if !ok {
            return nil, err
        }
        if me.Number == 1062 {
            // Duplicate key, check if it's the slug...
            if strings.Contains(me.Error(), "uix_slug") {
                return nil, fmt.Errorf("Duplicate display name.")
            }
        }
        return nil, err
    }
    // Update root_organization_id to the newly-inserted autoincrementing
    // primary key value
    newId, err := res.LastInsertId()
    if err != nil {
        return nil, err
    }

    qs = `
UPDATE organizations
SET root_organization_id = ?
WHERE id = ?
`

    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    _, err = stmt.Exec(newId, newId)
    if err != nil {
        return nil, err
    }

    // Add the creating user to the organization's group of users
    qs = `
INSERT INTO organization_users
(
  organization_id
, user_id
)
SELECT
  ?
, u.id
FROM users AS u
WHERE u.uuid = ?
`

    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    createdBy := s.userUuidFromIdentifier(sess.User)
    res, err = stmt.Exec(newId, createdBy)
    if err != nil {
        return nil, err
    }
    if createdBy == "" {
        err = fmt.Errorf("No such user %s", sess.User)
        return nil, err
    }
    affected, err := res.RowsAffected()
    if err != nil {
        return nil, err
    }
    if affected != 1 {
        // Can only happen if another thread has deleted the user in between
        // the above call to get the UUID and here, but let's be safe.
        err = fmt.Errorf("No such user %s", createdBy)
        return nil, err
    }

    err = tx.Commit()
    if err != nil {
        return nil, err
    }

    org := &pb.Organization{
        Uuid: uuid,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
    }
    s.log.L2("Created new root organization %s (%s)", slug, uuid)
    return org, nil
}

// Get the slug for a new child organization. The slug will be the
// concatenation of the root organization's slug and the supplied display name.
func childOrgSlug(root *pb.Organization, displayName string) string {
    return fmt.Sprintf("%s-%s", root.Slug, slug.Make(displayName))
}

// Adds a new organization that is a child of another organization, updating
// the root organization tree appropriately.
func (s *Storage) orgNewChild(
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied parent UUID is even valid
    parent := fields.Parent.Value
    parentOrg, err := s.orgFromIdentifier(parent)
    if err != nil {
        err := fmt.Errorf("No such organization found %s", parent)
        return nil, err
    }

    parentId := parentOrg.id
    parentUuid := parentOrg.pb.Uuid

    rootOrg, err := s.rootOrgFromParent(parentId)
    if err != nil {
        // This would only occur if something deleted the parent organization
        // record in between the above call to orgIdFromUuid() and here,
        // but whatever, let's be careful.
        err := fmt.Errorf("Organization %s was deleted", parent)
        return nil, err
    }

    displayName := fields.DisplayName.Value
    slug := childOrgSlug(rootOrg.pb, displayName)

    s.log.L2("Checking that new organization slug %s is unique.", slug)

    // Do a quick lookup of the newly-created slug to see if there's a
    // duplicate slug already and return an error if so.
    qs := `
SELECT COUNT(*) FROM organizations
WHERE slug = ?
`

    s.log.SQL(qs)

    rows, err := s.db.Query(qs, slug)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    var count int64
    for rows.Next() {
        err = rows.Scan(&count)
        if err != nil {
            return nil, err
        }
    }
    if count > 0 {
        err := fmt.Errorf(
            "Duplicate display name %s (within organization %s)",
            displayName,
            rootOrg.pb.Slug,
        )
        return nil, err
    }

    rootId := rootOrg.id
    rootGen := rootOrg.pb.Generation

    tx, err := s.db.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    nsLeft, nsRight, err := s.orgInsertIntoTree(tx, rootId, rootGen, parentId)
    if err != nil {
        return nil, err
    }

    uuid := util.Uuid4Char32()

    qs = `
INSERT INTO organizations (
  uuid
, display_name
, slug
, generation
, root_organization_id
, parent_organization_id
, nested_set_left
, nested_set_right
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    _, err = stmt.Exec(
        uuid,
        displayName,
        slug,
        1,
        rootId,
        parentId,
        nsLeft,
        nsRight,
    )
    if err != nil {
        me, ok := err.(*mysql.MySQLError)
        if !ok {
            return nil, err
        }
        if me.Number == 1062 {
            // Duplicate key, check if it's the slug...
            if strings.Contains(me.Error(), "uix_slug") {
                return nil, fmt.Errorf("Duplicate display name.")
            }
        }
        return nil, err
    }

    err = tx.Commit()
    if err != nil {
        return nil, err
    }

    org := &pb.Organization{
        Uuid: uuid,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
        ParentUuid: &pb.StringValue{Value: parentUuid},
    }
    s.log.L2("Created new child organization %s (%s) with parent %s",
              slug, uuid, parentUuid)
    return org, nil
}

// Inserts an organization into an org tree
func (s *Storage) orgInsertIntoTree(
    tx *sql.Tx,
    rootId int64,
    rootGeneration uint32,
    parentId int64,
) (int, int, error) {
    defer s.log.WithSection("iam/storage")()

    /*
    Updates the nested sets hierarchy for a new organization within
    the database. We use a slightly different algorithm for inserting
    a new organization that has a parent with no other children than
    when the new organization's parent already has children.

    In short, we use the following basic methodology:

    @rgt, @lft, @has_children = SELECT right_sequence - 1, left_sequence,
                                (SELECT COUNT(*) FROM organizations
                                WHERE parent_organization_id = parent_org_id)
                                FROM organizations
                                WHERE id = parent_org_id;
    if @has_children:
        UPDATE organizations SET right_sequence = right_sequence + 2
        WHERE right_sequence > @rgt
        AND root_organization_id = root_org_id;

        UPDATE organizations SET left_sequence = left_sequence + 2
        WHERE left_sequence > @rgt
        AND root_organization_id = root_org_id;
        
        left_sequence = @rgt + 1;
        right_sequence = @rgt + 2;
    else:
        UPDATE organizations SET right_sequence = right_sequence + 2
        WHERE right_sequence > @lft
        AND root_organization_id = root_org_id;

        UPDATE organizations SET left_sequence = left_sequence + 2
        WHERE left_sequence > @lft
        AND root_organization_id = root_org_id;
        
        left_sequence = @lft + 1;
        right_sequence = @lft + 2;

    UPDATE organizations SET generation = @rootGeneration + 1
    WHERE id = @rootId
    AND generation = @rootGeneration;

    return left_sequence, right_sequence
    */
    nsLeft := -1
    nsRight := -1
    numChildren := -1

    qs := `
SELECT
  nested_set_left
, nested_set_right
, (SELECT COUNT(*) FROM organizations
   WHERE parent_organization_id = ?) AS num_children
FROM organizations
WHERE id = ?
`

    s.log.SQL(qs)

    rows, err := tx.Query(qs, parentId, parentId)
    if err != nil {
        return -1, -1, err
    }
    err = rows.Err()
    if err != nil {
        return -1, -1, err
    }
    defer rows.Close()
    for rows.Next() {
        err = rows.Scan(&nsLeft, &nsRight, &numChildren)
        if err != nil {
            return -1, -1, err
        }
    }

    msg := "Inserting new organization into tree for root org %d. Prior to " +
           "insertion, new org's parent %d has left of %d, right of " +
           "%d, and %d children."
    s.log.L2(msg, rootId, parentId, nsLeft, nsRight, numChildren)

    compare := nsLeft
    if numChildren > 0 {
        compare = nsRight - 1
    }
    qs = `
UPDATE organizations SET nested_set_right = nested_set_right + 2
WHERE nested_set_right > ?
AND root_organization_id = ?
`

    s.log.SQL(qs)

    stmt, err := tx.Prepare(qs)
    if err != nil {
        return -1, -1, err
    }
    defer stmt.Close()
    _, err = stmt.Exec(
        compare,
        rootId,
    )
    if err != nil {
        return -1, -1, err
    }
    qs = `
UPDATE organizations SET nested_set_left = nested_set_left + 2
WHERE nested_set_left > ?
AND root_organization_id = ?
`

    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return -1, -1, err
    }
    defer stmt.Close()
    _, err = stmt.Exec(
        compare,
        rootId,
    )
    if err != nil {
        return -1, -1, err
    }
    qs = `
UPDATE organizations SET generation = generation + 1
WHERE id = ?
AND generation = ?
`

    s.log.SQL(qs)

    stmt, err = tx.Prepare(qs)
    if err != nil {
        return -1, -1, err
    }
    defer stmt.Close()
    res, err := stmt.Exec(
        rootId,
        rootGeneration,
    )
    if err != nil {
        return -1, -1, err
    }
    affected, err := res.RowsAffected()
    if err != nil {
        return -1, -1, err
    }
    if affected != 1 {
        // Concurrent update to this organization tree has been detected. Roll
        // back all the changes.
        tx.Rollback()
        return -1, -1, fmt.Errorf("Concurrent update detected.")
    }
    return compare + 1, compare + 2, nil
}

// Creates a new record for an organization
func (s *Storage) OrganizationCreate(
    sess *pb.Session,
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    if fields.Parent == nil {
        return s.orgNewRoot(sess, fields)
    } else {
        return s.orgNewChild(fields)
    }
}

// Updates information for an existing organization by examining the fields
// changed to the current fields values
func (s *Storage) OrganizationUpdate(
    before *pb.Organization,
    changed *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    uuid := before.Uuid
    qs := `
UPDATE organizations SET `
    changes := make(map[string]interface{}, 0)
    newOrg := &pb.Organization{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if changed.DisplayName != nil {
        newDisplayName := changed.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        changes["slug"] = newSlug
        newOrg.DisplayName = newDisplayName
        newOrg.Slug = newSlug
    } else {
        newOrg.DisplayName = before.DisplayName
        newOrg.Slug = before.Slug
    }
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + "\nWHERE uuid = ? AND generation = ?"

    s.log.SQL(qs)

    stmt, err := s.db.Prepare(qs)
    if err != nil {
        return nil, err
    }
    pargs := make([]interface{}, len(changes) + 2)
    x := 0
    for _, value := range changes {
        pargs[x] = value
        x++
    }
    pargs[x] = uuid
    x++
    pargs[x] = before.Generation
    _, err = stmt.Exec(pargs...)
    if err != nil {
        return nil, err
    }
    return newOrg, nil
}

// INSERTs and DELETEs user to organization mapping records. Returns the number
// of users added and removed to/from the organization.
func (s *Storage) OrganizationMembersSet(
    req *pb.OrganizationMembersSetRequest,
) (uint64, uint64, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied organization exists
    orgSearch := req.Organization
    orgId := s.orgIdFromIdentifier(orgSearch)
    if orgId == 0 {
        notFound := fmt.Errorf("No such organization found.")
        return 0, 0, notFound
    }

    tx, err := s.db.Begin()
    if err != nil {
        return 0, 0, err
    }
    defer tx.Rollback()

    // Look up user internal IDs for all supplied added and removed user
    // identifiers
    userIdsAdd := make([]uint64, 0)
    for _, identifier := range req.Add {
        userId := s.userIdFromIdentifier(identifier)
        if userId == 0 {
            // This will return a NotFound error when the request wanted to add
            // an unknown user to the organization
            return 0, 0, err
        }
        userIdsAdd = append(userIdsAdd, userId)
    }
    userIdsRemove := make([]uint64, 0)
    for _, identifier := range req.Remove {
        userId := s.userIdFromIdentifier(identifier)
        if userId == 0 {
            // This will return a NotFound error when the request wanted to
            // remove an unknown user to the organization
            return 0, 0, err
        }
        userIdsRemove = append(userIdsRemove, userId)
    }

    for _, addId := range userIdsAdd {
        for _, removeId := range userIdsRemove {
            if addId == removeId {
                // Asked to add and remove the same user...
            }
        }
    }

    qargs := make([]interface{}, 2 * (len(userIdsAdd) + len(userIdsRemove)))
    c := 0
    for _, userId := range userIdsAdd {
        qargs[c] = orgId
        c++
        qargs[c] = userId
        c++
    }
    addedQargs := c
    if len(userIdsRemove) > 0 {
        qargs[c] = orgId
        c++
        for _, userId := range userIdsRemove {
            qargs[c] = userId
            c++
        }
    }

    numAdded := int64(0)
    numRemoved := int64(0)
    if len(userIdsAdd) > 0 {
        qs := `
INSERT INTO organization_users (
  organization_id
, user_id
) VALUES
    `

        s.log.SQL(qs)

        for x, _ := range userIdsAdd {
            if x > 0 {
                qs = qs + "\n, (?, ?)"
            } else {
                qs = qs + "(?, ?)"
            }
        }
        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[0:c]...)
        if err != nil {
            return 0, 0, err
        }
        numAdded, err = res.RowsAffected()
        if err != nil {
            return 0, 0, err
        }
    }

    if len(userIdsRemove) > 0 {
        qs := `
DELETE FROM organization_users
WHERE organization_id = ?
AND user_id ` + sqlutil.InParamString(len(userIdsRemove)) + `
`
        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[0:c]...)
        if err != nil {
            return 0, 0, err
        }
        numAdded, err = res.RowsAffected()
        if err != nil {
            return 0, 0, err
        }
    }

    if len(userIdsRemove) > 0 {
        qs := `
DELETE FROM organization_users
WHERE organization_id = ?
AND user_id ` + sqlutil.InParamString(len(userIdsRemove)) + `
`
        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[addedQargs:c]...)
        if err != nil {
            return 0, 0, err
        }
        numRemoved, err = res.RowsAffected()
        if err != nil {
            return 0, 0, err
        }
    }

    err = tx.Commit()
    if err != nil {
        return 0, 0, err
    }
    return uint64(numAdded), uint64(numRemoved), nil
}

// Returns the users belonging to an organization
func (s *Storage) OrganizationMembersList(
    req *pb.OrganizationMembersListRequest,
) (*sql.Rows, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied organization exists
    orgSearch := req.Organization
    orgId := s.orgIdFromIdentifier(orgSearch)
    if orgId == 0 {
        notFound := fmt.Errorf("No such organization found.")
        return nil, notFound
    }
    // Below, we use the nested sets modeling to identify users for the target
    // organization and all of that organization's predecessors (ascendants).
    // This is because the membership of a child organization is composed of
    // the set of memberships of all organizations "above" the target
    // organization in the same tree
    qs := `
SELECT
  u.uuid
, u.display_name
, u.email
, u.slug
FROM organizations AS o1
JOIN organizations AS o2
 ON o1.nested_set_left BETWEEN o2.nested_set_left and o2.nested_set_right
 AND o1.root_organization_id = o2.root_organization_id
JOIN organization_users AS ou
 ON ou.organization_id = o2.id
JOIN users AS u
 ON ou.user_id = u.id
WHERE o1.id = ?
`
    s.log.SQL(qs)

    rows, err := s.db.Query(qs, orgId)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}
