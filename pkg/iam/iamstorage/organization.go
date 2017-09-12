package iamstorage

import (
    "fmt"
    "database/sql"

    "github.com/gosimple/slug"
    "github.com/golang/protobuf/proto"
    "github.com/jaypipes/sqlb"

    "github.com/jaypipes/procession/pkg/errors"
    "github.com/jaypipes/procession/pkg/sqlutil"
    "github.com/jaypipes/procession/pkg/storage"
    "github.com/jaypipes/procession/pkg/util"
    pb "github.com/jaypipes/procession/proto"
)

var (
    orgSortFields = []*sqlutil.SortFieldInfo{
        &sqlutil.SortFieldInfo{
            Name: "uuid",
            Unique: true,
        },
        &sqlutil.SortFieldInfo{
            Name: "display_name",
            Unique: false,
            Aliases: []string{
                "name",
                "display name",
                "display_name",
            },
        },
    }
)

// Simple wrapper struct that allows us to pass the internal ID for an
// organization around with a protobuf message of the external representation
// of the organization
type orgRecord struct {
    pb *pb.Organization
    id int64
    rootOrgId int64
}

// A generator that returns a function that returns a string value of a sort
// field after looking up an organization by UUID
func (s *IAMStorage) orgSortFieldByUuid(
    uuid string,
    sortField *pb.SortField,
) func () string {
    f := func () string {
        qs := fmt.Sprintf(
            "SELECT %s FROM organizations WHERE uuid = ?",
            sortField.Field,
        )
        qargs := []interface{}{uuid}
        rows, err := s.Rows(qs, qargs...)
        if err != nil {
            return ""
        }
        defer rows.Close()
        var sortVal string
        for rows.Next() {
            err = rows.Scan(&sortVal)
            if err != nil {
                return ""
            }
            return sortVal
        }
        return ""
    }
    return f
}

// Returns a RowIterator yielding organizations matching a set of supplied
// filters
func (s *IAMStorage) OrganizationList(
    req *pb.OrganizationListRequest,
) (storage.RowIterator, error) {
    sess := req.Session
    filters := req.Filters
    opts := req.Options
    err := sqlutil.NormalizeSortFields(
        opts,
        &orgSortFields,
    )
    if err != nil {
        return nil, err
    }

    user, err := s.userRecord(sess.User)
    if err != nil {
        return nil, err
    }
    qs := `
SELECT
  o.uuid
, o.display_name
, o.slug
, o.generation
, po.display_name as parent_display_name
, po.slug as parent_slug
, po.uuid as parent_uuid
FROM organizations AS o
LEFT JOIN organizations AS po
  ON o.parent_organization_id = po.id
LEFT JOIN (
  SELECT o1.id
  FROM organizations AS o1
  JOIN organizations AS o2
    ON o1.root_organization_id = o2.root_organization_id
    AND o1.nested_set_left BETWEEN o2.nested_set_left AND o2.nested_set_right
  JOIN organization_users AS ou
    ON o2.id = ou.organization_id
    AND ou.user_id = ?
) AS private_orgs
  ON o.id = private_orgs.id
WHERE (
  o.visibility = 1
  OR (o.visibility = 0 AND private_orgs.id IS NOT NULL)
`
    qargs := make([]interface{}, 0)
    qargs = append(qargs, user.id)
    if filters.Identifiers != nil {
        qs = qs + "AND ("
        for x, search := range filters.Identifiers {
            orStr := ""
            if x > 0 {
                orStr = "\nOR "
            }
            colName := "o.uuid"
            if ! util.IsUuidLike(search) {
                colName = "o.slug"
                search = slug.Make(search)
            }
            qs = qs + fmt.Sprintf(
                "%s%s = ?",
                orStr,
                colName,
            )
            qargs = append(qargs, search)
        }
        qs = qs + ")"
    }
    qs = qs + ")"
    if opts.Marker != "" && len(opts.SortFields) > 0 {
        sqlutil.AddMarkerWhere(
            &qs,
            opts,
            "o",
            true,
            &qargs,
            orgSortFields,
            s.orgSortFieldByUuid(opts.Marker, opts.SortFields[0]),
        )
    }
    sqlutil.AddOrderBy(&qs, opts, "o")
    qs = qs + "\nLIMIT ?"
    qargs = append(qargs, opts.Limit)

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Deletes an organization, all organization members and child organizations,
// and any resources the organization owns
func (s *IAMStorage) OrganizationDelete(
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
    var parentName sql.NullString
    var parentSlug sql.NullString
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
, po.display_name as parent_display_name
, po.slug as parent_slug
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

    rows, err := s.Rows(qs, qargs...)
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
            &parentName,
            &parentSlug,
            &parentUuid,
            &parentGeneration,
        )
        if err != nil {
            return err
        }
        break
    }

    if orgId == 0 {
        return errors.NOTFOUND("organization", search)
    }

    before := &pb.Organization{
        Uuid: orgUuid,
        DisplayName: orgDisplayName,
        Slug: orgSlug,
        Generation: orgGeneration,
    }
    if parentName.Valid {
        parent := &pb.Organization{
            DisplayName: parentName.String,
            Slug: parentSlug.String,
            Uuid: parentUuid.String,
            Generation: uint32(parentGeneration.Int64),
        }
        before.Parent = parent
    }

    msg := "Deleting organization %d (left: %d, right %d)"
    s.log.L2(msg, orgId, nsLeft, nsRight)

    tx, err := s.Begin()
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
func (s *IAMStorage) OrganizationGet(
    search string,
) (*pb.Organization, error) {
    m := s.Meta()
    otbl := m.TableDef("organizations").As("o")
    potbl := m.TableDef("organizations").As("po")
    colOrgUuid := otbl.Column("uuid")
    colOrgDisplayName := otbl.Column("display_name")
    colOrgSlug := otbl.Column("slug")
    colOrgGen := otbl.Column("generation")
    colOrgParentId := otbl.Column("parent_organization_id")
    colPOOrgId := potbl.Column("id")
    colPOSlug := potbl.Column("slug")
    colPOUuid := potbl.Column("uuid")
    colPODisplayName := potbl.Column("display_name")
    q := sqlb.Select(
        colOrgUuid,
        colOrgDisplayName,
        colOrgSlug,
        colOrgGen,
        colPOUuid,
        colPOSlug,
        colPODisplayName,
    )
    q.OuterJoin(potbl, sqlb.Equal(colOrgParentId, colPOOrgId))
    if util.IsUuidLike(search) {
        q.Where(sqlb.Equal(colOrgUuid, util.UuidFormatDb(search)))
    } else {
        q.Where(
            sqlb.Or(
                sqlb.Equal(colOrgDisplayName, search),
                sqlb.Equal(colOrgSlug, search),
            ),
        )
    }
    qs, qargs := q.StringArgs()

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    found := false
    org := pb.Organization{}
    for rows.Next() {
        if found {
            return nil, errors.TOO_MANY_MATCHES(search)
        }
        var parentName sql.NullString
        var parentSlug sql.NullString
        var parentUuid sql.NullString
        err = rows.Scan(
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &parentName,
            &parentSlug,
            &parentUuid,
        )
        if err != nil {
            return nil, err
        }
        if parentName.Valid {
            parent := &pb.Organization{
                DisplayName: parentName.String,
                Slug: parentSlug.String,
                Uuid: parentUuid.String,
            }
            org.Parent = parent
        }
        found = true
    }
    return &org, nil
}

// Given an identifier (slug or UUID), return the organization's internal
// integer ID. Returns 0 if the organization could not be found.
func (s *IAMStorage) orgIdFromIdentifier(identifier string) int64 {
    qargs := make([]interface{}, 0)
    qs := `
SELECT id FROM
organizations
WHERE `
    qs = orgBuildWhere(qs, identifier, &qargs)

    rows, err := s.Rows(qs, qargs...)
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
func (s *IAMStorage) rootOrgIdFromIdentifier(identifier string) uint64 {
    qargs := make([]interface{}, 0)
    qs := `
SELECT root_organization_id
FROM organizations
WHERE `
    qs = orgBuildWhere(qs, identifier, &qargs)

    rows, err := s.Rows(qs, qargs...)
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
func (s *IAMStorage) orgIdsFromParentId(
    parentId uint64,
) []interface{} {
    qs := `
SELECT o1.id
FROM organizations AS o1
JOIN organizations AS o2
ON o1.root_organization_id = o2.root_organization_id
AND o1.nested_set_left BETWEEN o2.nested_set_left AND o2.nested_set_right
WHERE o2.id = ?
`
    rows, err := s.Rows(qs, parentId)
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
func (s *IAMStorage) orgIdFromUuid(
    uuid string,
) int {
    qs := `
SELECT id
FROM organizations
WHERE uuid = ?
`
    rows, err := s.Rows(qs, uuid)
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
func (s *IAMStorage) orgFromIdentifier(
    identifier string,
) (*orgRecord, error) {
    qargs := make([]interface{}, 0)
    qs := `
SELECT
  o.id
, o.uuid
, o.display_name
, o.slug
, o.generation
, o.root_organization_id
, po.display_name as parent_display_name
, po.slug as parent_slug
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

    rows, err := s.Rows(qs, qargs...)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    org := &pb.Organization{}
    orgWithId := &orgRecord{
        pb: org,
    }
    for rows.Next() {
        var parentName sql.NullString
        var parentSlug sql.NullString
        var parentUuid sql.NullString
        err = rows.Scan(
            &orgWithId.id,
            &org.Uuid,
            &org.DisplayName,
            &org.Slug,
            &org.Generation,
            &orgWithId.rootOrgId,
            &parentName,
            &parentSlug,
            &parentUuid,
        )
        if err != nil {
            return nil, err
        }
        if parentName.Valid {
            parent := &pb.Organization{
                DisplayName: parentName.String,
                Slug: parentSlug.String,
                Uuid: parentUuid.String,
            }
            org.Parent = parent
        }
    }
    return orgWithId, nil
}

// TODO(jaypipes): Consolidate this and rootOrgFromParent() into a single
// function
// Given a parent org UUID, returns that parent's root organization or an error
// if the root organization could not be found
func (s *IAMStorage) rootOrgFromParentUuid(
    parentUuid string,
) (*orgRecord, error) {
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
WHERE po.uuid = ?
`
    rows, err := s.Rows(qs, parentUuid)
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
    return &orgRecord{
        pb: org,
        id: rootId,
    }, nil
}

// Given an integer parent org ID, returns that parent's root organization or
// an error if the root organization could not be found
func (s *IAMStorage) rootOrgFromParent(
    parentId int64,
) (*orgRecord, error) {
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
    rows, err := s.Rows(qs, parentId)
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
    return &orgRecord{
        pb: org,
        id: rootId,
    }, nil
}

// Adds a new top-level organization record
func (s *IAMStorage) orgNewRoot(
    sess *pb.Session,
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/storage")()

    tx, err := s.Begin()
    if err != nil {
        return nil, err
    }
    defer tx.Rollback()

    uuid := util.Uuid4Char32()
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    visibility := uint32(fields.Visibility)

    qs := `
INSERT INTO organizations (
  uuid
, display_name
, slug
, generation
, visibility
, root_organization_id
, parent_organization_id
, nested_set_left
, nested_set_right
) VALUES (?, ?, ?, ?, ?, NULL, NULL, 1, 2)
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
        visibility,
    )
    if err != nil {
        if sqlutil.IsDuplicateKey(err) {
            // Duplicate key, check if it's the slug...
            if sqlutil.IsDuplicateKeyOn(err, "uix_slug") {
                return nil, errors.DUPLICATE("display name", displayName)
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
func (s *IAMStorage) orgNewChild(
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied parent identifier is even valid
    parent := fields.Parent.Value
    parentOrg, err := s.orgFromIdentifier(parent)
    if err != nil {
        err := fmt.Errorf("No such organization found %s", parent)
        return nil, err
    }

    parentId := parentOrg.id

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
    visibility := fields.Visibility

    // A child organization of a private parent cannot be marked public...
    parVisibility := parentOrg.pb.Visibility

    if (parVisibility == pb.Visibility_PRIVATE &&
            visibility == pb.Visibility_PUBLIC) {
        return nil, errors.INVALID_PUBLIC_CHILD_PRIVATE_PARENT
    }

    s.log.L2("Checking that new organization slug %s is unique.", slug)

    // Do a quick lookup of the newly-created slug to see if there's a
    // duplicate slug already and return an error if so.
    qs := `
SELECT COUNT(*) FROM organizations
WHERE slug = ?
`
    rows, err := s.Rows(qs, slug)
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

    tx, err := s.Begin()
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
, visibility
, root_organization_id
, parent_organization_id
, nested_set_left
, nested_set_right
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        uint32(visibility),
        rootId,
        parentId,
        nsLeft,
        nsRight,
    )
    if err != nil {
        if sqlutil.IsDuplicateKey(err) {
            // Duplicate key, check if it's the slug...
            if sqlutil.IsDuplicateKeyOn(err, "uix_slug") {
                return nil, errors.DUPLICATE("display name", displayName)
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
        Parent: parentOrg.pb,
    }
    s.log.L2("Created new child organization %s (%s) with parent %s",
              slug, uuid, parentOrg.pb.Uuid)
    return org, nil
}

// Inserts an organization into an org tree
func (s *IAMStorage) orgInsertIntoTree(
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
func (s *IAMStorage) OrganizationCreate(
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
func (s *IAMStorage) OrganizationUpdate(
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
        Parent: before.Parent,
    }
    if changed.DisplayName != nil {
        // If there is a parent, we need to ensure that the new slug includes
        // the root organization slug
        var newDisplayName string
        var newSlug string
        if before.Parent != nil {
            parentUuid := before.Parent.Uuid
            rootOrg, err := s.rootOrgFromParentUuid(parentUuid)
            if err != nil {
                err := fmt.Errorf("Organization %s was deleted", parentUuid)
                return nil, err
            }
            newDisplayName = changed.DisplayName.Value
            newSlug = childOrgSlug(rootOrg.pb, newDisplayName)
        } else {
            newDisplayName = changed.DisplayName.Value
            newSlug = slug.Make(newDisplayName)
        }
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

    stmt, err := s.Prepare(qs)
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
func (s *IAMStorage) OrganizationMembersSet(
    req *pb.OrganizationMembersSetRequest,
) (uint64, uint64, error) {
    defer s.log.WithSection("iam/storage")()

    // First verify the supplied organization exists
    orgSearch := req.Organization
    orgId := s.orgIdFromIdentifier(orgSearch)
    if orgId == 0 {
        return 0, 0, errors.NOTFOUND("organization", orgSearch)
    }

    tx, err := s.Begin()
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
            return 0, 0, errors.NOTFOUND("user", identifier)
        }
        userIdsAdd = append(userIdsAdd, userId)
    }
    userIdsRemove := make([]uint64, 0)
    for _, identifier := range req.Remove {
        userId := s.userIdFromIdentifier(identifier)
        if userId == 0 {
            return 0, 0, errors.NOTFOUND("user", identifier)
        }
        userIdsRemove = append(userIdsRemove, userId)
    }

    for x, addId := range userIdsAdd {
        for _, removeId := range userIdsRemove {
            if addId == removeId {
                // Asked to add and remove the same user...
                err = fmt.Errorf(
                    "Cannot both add and remove user %s.",
                    req.Add[x],
                )
                return 0, 0, err
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
        for x, _ := range userIdsAdd {
            if x > 0 {
                qs = qs + "\n, (?, ?)"
            } else {
                qs = qs + "(?, ?)"
            }
        }

        s.log.SQL(qs)

        stmt, err := tx.Prepare(qs)
        if err != nil {
            return 0, 0, err
        }
        defer stmt.Close()
        res, err := stmt.Exec(qargs[0:addedQargs]...)
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
func (s *IAMStorage) OrganizationMembersList(
    req *pb.OrganizationMembersListRequest,
) (storage.RowIterator, error) {
    // First verify the supplied organization exists
    orgSearch := req.Organization
    orgId := s.orgIdFromIdentifier(orgSearch)
    if orgId == 0 {
        return nil, errors.NOTFOUND("organization", orgSearch)
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
    rows, err := s.Rows(qs, orgId)
    if err != nil {
        return nil, err
    }
    return rows, nil
}
