package db

import (
    "fmt"
    "log"
    "database/sql"
    "strings"

    "github.com/gosimple/slug"

    pb "github.com/jaypipes/procession/proto"
    "github.com/jaypipes/procession/pkg/util"
)

// Returns a sql.Rows yielding organizations matching a set of supplied filters
func OrganizationList(
    db *sql.DB,
    filters *pb.OrganizationListFilters,
) (*sql.Rows, error) {
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
        qs = qs + " WHERE "
        if filters.Uuids != nil {
            qs = qs + fmt.Sprintf(
                "o.uuid IN (%s)",
                inParamString(len(filters.Uuids)),
            )
            for _,  val := range filters.Uuids {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
        if filters.DisplayNames != nil {
            if qidx > 0{
                qs = qs + "\n AND "
            }
            qs = qs + fmt.Sprintf(
                "o.display_name IN (%s)",
                inParamString(len(filters.DisplayNames)),
            )
            for _,  val := range filters.DisplayNames {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
        if filters.Slugs != nil {
            if qidx > 0 {
                qs = qs + "\n AND "
            }
            qs = qs + fmt.Sprintf(
                "o.slug IN (%s)",
                inParamString(len(filters.Slugs)),
            )
            for _,  val := range filters.Slugs {
                qargs[qidx] = strings.Trim(val, trimChars)
                qidx++
            }
        }
    }

    rows, err := db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}

// Returns a pb.Organization record filled with information about a reqed
// organization.
func OrganizationGet(
    db *sql.DB,
    search string,
) (*pb.Organization, error) {
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

    rows, err := db.Query(qs, qargs...)
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
func orgIdFromIdentifier(db *sql.DB, identifier string) uint64 {
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT id FROM organizations WHERE "
    qs = orgBuildWhere(qs, identifier, &qargs)

    rows, err := db.Query(qs, qargs...)
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

// Returns the integer ID of an organization given its UUID. Returns -1 if an
// organization with the UUID was not found
func orgIdFromUuid(db *sql.DB, uuid string) int {
    qs := "SELECT id FROM organizations WHERE uuid = ?"
    rows, err := db.Query(qs, uuid)
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
func orgBuildWhere(qs string, search string, qargs *[]interface{}) string {
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

// Given an integer parent org ID, returns that parent's root organization ID
// and generation. Returns -1 for both values if no such organization with such
// a parent ID was found.
func rootIdAndGenerationFromParent(db *sql.DB, parentId int) (int, int) {
    qs := `
SELECT
  ro.id
, ro.generation
FROM organizations AS po
JOIN organizations AS ro
  ON po.root_organization_id = ro.id
WHERE po.id = ?
`
    rows, err := db.Query(qs, parentId)
    if err != nil {
        return -1, -1
    }
    err = rows.Err()
    if err != nil {
        return -1, -1
    }
    defer rows.Close()
    rootId := -1
    rootGen := -1
    for rows.Next() {
        err = rows.Scan(&rootId, &rootGen)
        if err != nil {
            return -1, -1
        }
    }
    return rootId, rootGen
}

// Adds a new top-level organization record
func orgNewRoot(
    sess *pb.Session,
    db *sql.DB,
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    tx, err := db.Begin()
    if err != nil {
        log.Fatal(err)
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
    stmt, err := tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    defer stmt.Close()
    res, err := stmt.Exec(
        uuid,
        displayName,
        slug,
        1,
    )
    if err != nil {
        return nil, err
    }
    // Update root_organization_id to the newly-inserted autoincrementing
    // primary key value
    newId, err := res.LastInsertId()
    if err != nil {
        log.Fatal(err)
    }

    qs = `
UPDATE organizations
SET root_organization_id = ?
WHERE id = ?
`
    stmt, err = tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
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
    stmt, err = tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
    }
    defer stmt.Close()
    createdBy := userUuidFromIdentifier(db, sess.User)
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
    info("Created new root organization %s (%s)", slug, uuid)
    return org, nil
}

// Adds a new organization that is a child of another organization, updating
// the root organization tree appropriately.
func orgNewChild(db *sql.DB, fields *pb.OrganizationSetFields) (*pb.Organization, error) {
    // First verify the supplied parent UUID is even valid
    parentUuid := fields.ParentUuid.Value
    parentId := orgIdFromUuid(db, parentUuid)
    if parentId == -1 {
        err := fmt.Errorf("No such organization found with UUID %s", parentUuid)
        return nil, err
    }

    rootId, rootGen := rootIdAndGenerationFromParent(db, parentId)
    if rootId == -1 {
        // This would only occur if something deleted the parent organization
        // record in between the above call to orgIdFromUuid() and here,
        // but whatever, let's be careful.
        err := fmt.Errorf("Organization with UUID %s was deleted", parentUuid)
        return nil, err
    }

    tx, err := db.Begin()
    if err != nil {
        log.Fatal(err)
    }
    defer tx.Rollback()

    nsLeft, nsRight, err := orgInsertIntoTree(tx, rootId, rootGen, parentId)
    if err != nil {
        log.Fatal(err)
    }

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
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`
    stmt, err := tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
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
    info("Created new child organization %s (%s) with parent %s",
         slug, uuid, parentUuid)
    return org, nil
}

// Inserts an organization into an org tree
func orgInsertIntoTree(tx *sql.Tx, rootId int, rootGeneration int, parentId int) (int, int, error) {
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
    debug(msg, rootId, parentId, nsLeft, nsRight, numChildren)

    compare := nsLeft
    if numChildren > 0 {
        compare = nsRight - 1
    }
    qs = `
UPDATE organizations SET nested_set_right = nested_set_right + 2
WHERE nested_set_right > ?
AND root_organization_id = ?
`
    stmt, err := tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
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
    stmt, err = tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
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
    stmt, err = tx.Prepare(qs)
    if err != nil {
        log.Fatal(err)
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
        log.Fatal(err)
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
func OrganizationCreate(
    sess *pb.Session,
    db *sql.DB,
    fields *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    if fields.ParentUuid == nil {
        return orgNewRoot(sess, db, fields)
    } else {
        return orgNewChild(db, fields)
    }
}

// Updates information for an existing organization by examining the fields
// changed to the current fields values
func OrganizationUpdate(
    db *sql.DB,
    before *pb.Organization,
    changed *pb.OrganizationSetFields,
) (*pb.Organization, error) {
    uuid := before.Uuid
    qs := "UPDATE organizations SET "
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

    qs = qs + " WHERE uuid = ? AND generation = ?"

    stmt, err := db.Prepare(qs)
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
func OrganizationMembersSet(
    db *sql.DB,
    req *pb.OrganizationMembersSetRequest,
) (uint64, uint64, error) {
    // First verify the supplied organization exists
    orgSearch := req.Organization
    orgId := orgIdFromIdentifier(db, orgSearch)
    if orgId == 0 {
        notFound := fmt.Errorf("No such organization found.")
        return 0, 0, notFound
    }

    tx, err := db.Begin()
    if err != nil {
        log.Fatal(err)
    }
    defer tx.Rollback()

    // Look up user internal IDs for all supplied added and removed user
    // identifiers
    userIdsAdd := make([]uint64, 0)
    for _, identifier := range req.Add {
        userId := userIdFromIdentifier(db, identifier)
        if userId == 0 {
            // This will return a NotFound error when the request wanted to add
            // an unknown user to the organization
            return 0, 0, err
        }
        userIdsAdd = append(userIdsAdd, userId)
    }
    userIdsRemove := make([]uint64, 0)
    for _, identifier := range req.Remove {
        userId := userIdFromIdentifier(db, identifier)
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
        for x, _ := range userIdsAdd {
            if x > 0 {
                qs = qs + "\n, (?, ?)"
            } else {
                qs = qs + "(?, ?)"
            }
        }
        info(qs)
        stmt, err := tx.Prepare(qs)
        if err != nil {
            log.Fatal(err)
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
AND user_id IN (` + inParamString(len(userIdsRemove)) + `)
`
        info(qs)
        stmt, err := tx.Prepare(qs)
        if err != nil {
            log.Fatal(err)
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
