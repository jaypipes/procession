package storage

import (
    "fmt"
    "database/sql"
    "strings"

    "github.com/gosimple/slug"

    "github.com/jaypipes/procession/pkg/util"
    "github.com/jaypipes/procession/pkg/sqlutil"
    pb "github.com/jaypipes/procession/proto"
)

// Returns a sql.Rows yielding users matching a set of supplied filters
func (s *Storage) UserList(
    filters *pb.UserListFilters,
) (*sql.Rows, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    numWhere := 0
    if filters.Uuids != nil {
        numWhere = numWhere + len(filters.Uuids)
    }
    if filters.DisplayNames != nil {
        numWhere = numWhere + len(filters.DisplayNames)
    }
    if filters.Emails != nil {
        numWhere = numWhere + len(filters.Emails)
    }
    if filters.Slugs != nil {
        numWhere = numWhere + len(filters.Slugs)
    }
    qargs := make([]interface{}, numWhere)
    qidx := 0
    qs := `
SELECT
  uuid
, email
, display_name
, slug
, generation
FROM users
`
    if numWhere > 0 {
        qs = qs + "WHERE "
        if filters.Uuids != nil {
            qs = qs + fmt.Sprintf(
                "uuid %s",
                sqlutil.InParamString(len(filters.Uuids)),
            )
            for _,  val := range filters.Uuids {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.DisplayNames != nil {
            if qidx > 0{
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "display_name %s",
                sqlutil.InParamString(len(filters.DisplayNames)),
            )
            for _,  val := range filters.DisplayNames {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.Emails != nil {
            if qidx > 0 {
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "email %s",
                sqlutil.InParamString(len(filters.Emails)),
            )
            for _,  val := range filters.Emails {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
        if filters.Slugs != nil {
            if qidx > 0 {
                qs = qs + "\nAND "
            }
            qs = qs + fmt.Sprintf(
                "slug %s",
                sqlutil.InParamString(len(filters.Slugs)),
            )
            for _,  val := range filters.Slugs {
                qargs[qidx] = strings.TrimSpace(val)
                qidx++
            }
        }
    }

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

// Returns a list of user IDs for users belonging to an entire organization
// tree excluding a supplied user ID
func (s *Storage) usersInOrgTreeExcluding(
    rootOrgId uint64,
    excludeUserId uint64,
) ([]uint64, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    qs := `
SELECT ou.user_id
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
WHERE o.root_organization_id = ?
AND ou.user_id != ?
`
    out := make([]uint64, 0)
    rows, err := s.db.Query(qs, rootOrgId, excludeUserId)
    if err != nil {
        return nil, err
    }
    if err = rows.Err(); err != nil {
        return nil, err
    }
    for rows.Next() {
        var userId uint64
        err = rows.Scan(&userId)
        if err != nil {
            return nil, err
        }
        out = append(out, userId)
    }
    return out, nil
}

// Returns a list of user IDs for users belonging to one specific organization
// (not the entire tree) excluding a supplied user ID
func (s *Storage) usersInOrgExcluding(
    orgId uint64,
    excludeUserId uint64,
) ([]uint64, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    qs := `
SELECT ou.user_id
FROM organization_users AS ou
WHERE ou.organization_id = ?
AND ou.user_id != ?
`
    out := make([]uint64, 0)
    rows, err := s.db.Query(qs, orgId, excludeUserId)
    if err != nil {
        return nil, err
    }
    if err = rows.Err(); err != nil {
        return nil, err
    }
    for rows.Next() {
        var userId uint64
        err = rows.Scan(&userId)
        if err != nil {
            return nil, err
        }
        out = append(out, userId)
    }
    return out, nil
}

type orgToDelete struct {
    id uint64
    generation uint64
}

func errCannotDeleteUserOrphanedOrg(
    user string,
    org string,
) error {
    return fmt.Errorf(`
Unable to delete user %s. This user is the sole member of organization %s which
has child organizations that would be orphaned by deleting the user. Please add
another user to organization %s's membership or manually delete the
organization.`, user, org, org)
}

// Deletes a user, their membership in any organizations and all resources they
// have created. Also deletes root organizations that only the user is a member of.
func (s *Storage) UserDelete(
    search string,
) error {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        return fmt.Errorf("No such user found.")
    }

    // Identify root organizations that the user is a member of. If those
    // organizations have child organizations that have users *other* than the
    // user we'd like to delete and there are no other users associated with
    // the *root* organization, return an error saying the user needs to
    // transfer ownership of the root organization by adding another user or
    // delete the organization entirely.
    qs := `
SELECT
  o.id
, o.uuid
, o.generation
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
WHERE ou.user_id = ?
AND o.parent_organization_id IS NULL
`
    rootOrgs, err := s.db.Query(qs, userId)
    if err != nil {
        return err
    }
    err = rootOrgs.Err()
    if err != nil {
        return err
    }
    defer rootOrgs.Close()

    orgsToDelete := make([]*orgToDelete, 0)
    for rootOrgs.Next() {
        var orgId uint64
        var orgUuid string
        var orgGeneration uint64
        err = rootOrgs.Scan(&orgId, &orgUuid, &orgGeneration)
        if err != nil {
            return err
        }
        otherUsers, err := s.usersInOrgTreeExcluding(orgId, userId)
        if err != nil {
            return err
        }
        if len(otherUsers) == 0 {
            // This is a root organization and there's no other users in the
            // entire organization tree, so mark it for deletion. There's no
            // point keeping it around.
            toDelete := &orgToDelete{
                id: orgId,
                generation: orgGeneration,
            }
            orgsToDelete = append(orgsToDelete, toDelete)
            continue
        } else {
            rootOtherUsers, err := s.usersInOrgExcluding(orgId, userId)
            if err != nil {
                return err
            }
            if len(rootOtherUsers) == 0 {
                // there are NOT other users associated to the root
                // organization but there ARE other users associated to child
                // organizations in the tree. Deleting the target user here
                // would leave this organization "orphaned" because there would
                // be no member of the root organization and thus no user could
                // delete the organization, add child organizations or add
                // members to the root organization. So, return an error to the
                // caller saying ownership must be transferred for this
                // organization or the organization needs to first be deleted.
                err = errCannotDeleteUserOrphanedOrg(search, orgUuid)
                return err
            }
        }
    }

    tx, err := s.db.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()

    if len(orgsToDelete) > 0 {
        orgsInParam := sqlutil.InParamString(len(orgsToDelete))
        qargs := make([]interface{}, len(orgsToDelete))
        for x, orgId := range orgsToDelete {
            qargs[x] = orgId
        }
        qs = `
DELETE FROM organization_users
WHERE organization_id ` + orgsInParam + `
`
        stmt, err := tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        _, err = stmt.Exec(qargs...)
        if err != nil {
            return err
        }

        qs = `
DELETE FROM organizations
WHERE id ` + orgsInParam + `
`
        stmt, err = tx.Prepare(qs)
        if err != nil {
            return err
        }
        defer stmt.Close()
        _, err = stmt.Exec(qargs...)
        if err != nil {
            return err
        }
    }

    qs = `
DELETE FROM organization_users
WHERE user_id = ?
`
    stmt, err := tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    _, err = stmt.Exec(userId)
    if err != nil {
        return err
    }

    qs = `
DELETE FROM users
WHERE id = ?
`
    stmt, err = tx.Prepare(qs)
    if err != nil {
        return err
    }
    defer stmt.Close()
    _, err = stmt.Exec(userId)
    if err != nil {
        return err
    }

    err = tx.Commit()
    if err != nil {
        return err
    }
    return nil
}

// Given an identifier (email, slug, or UUID), return the user's internal
// integer ID. Returns 0 if the user could not be found.
func (s *Storage) userIdFromIdentifier(
    identifier string,
) uint64 {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT id FROM users WHERE "
    qs = buildUserGetWhere(qs, identifier, &qargs)

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

// Given an identifier (email, slug, or UUID), return the user's UUID. Returns
// empty string if the user could not be found.
func (s *Storage) userUuidFromIdentifier(
    identifier string,
) string {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    var err error
    qargs := make([]interface{}, 0)
    qs := "SELECT uuid FROM users WHERE "
    qs = buildUserGetWhere(qs, identifier, &qargs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return ""
    }
    err = rows.Err()
    if err != nil {
        return ""
    }
    defer rows.Close()
    output := ""
    for rows.Next() {
        err = rows.Scan(&output)
        if err != nil {
            return ""
        }
        break
    }
    return output
}

// Builds the WHERE clause for single user search by identifier
func buildUserGetWhere(
    qs string,
    search string,
    qargs *[]interface{},
) string {
    if util.IsUuidLike(search) {
        qs = qs + "uuid = ?"
        *qargs = append(*qargs, util.UuidFormatDb(search))
    } else if util.IsEmailLike(search) {
        qs = qs + "email = ?"
        *qargs = append(*qargs, strings.TrimSpace(search))
    } else {
        qs = qs + "display_name = ? OR slug = ?"
        *qargs = append(*qargs, search)
        *qargs = append(*qargs, search)
    }
    return qs
}

// Returns a pb.User record filled with information about a requested user.
func (s *Storage) UserGet(
    search string,
) (*pb.User, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    qargs := make([]interface{}, 0)
    qs := `
SELECT
  uuid
, email
, display_name
, slug
, generation
FROM users
WHERE `
    qs = buildUserGetWhere(qs, search, &qargs)

    rows, err := s.db.Query(qs, qargs...)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    user := pb.User{}
    for rows.Next() {
        err = rows.Scan(
            &user.Uuid,
            &user.Email,
            &user.DisplayName,
            &user.Slug,
            &user.Generation,
        )
        if err != nil {
            return nil, err
        }
        break
    }
    return &user, nil
}

// Creates a new record for a user
func (s *Storage) UserCreate(
    fields *pb.UserSetFields,
) (*pb.User, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    qs := `
INSERT INTO users (uuid, email, display_name, slug, generation)
VALUES (?, ?, ?, ?, ?)
`
    stmt, err := s.db.Prepare(qs)
    if err != nil {
        return nil, err
    }
    uuid := util.Uuid4Char32()
    email := fields.Email.Value
    displayName := fields.DisplayName.Value
    slug := slug.Make(displayName)
    _, err = stmt.Exec(
        uuid,
        email,
        displayName,
        slug,
        1,
    )
    if err != nil {
        return nil, err
    }
    user := &pb.User{
        Uuid: uuid,
        Email: email,
        DisplayName: displayName,
        Slug: slug,
        Generation: 1,
    }
    return user, nil
}

// Sets information for a user
func (s *Storage) UserUpdate(
    before *pb.User,
    changed *pb.UserSetFields,
) (*pb.User, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    uuid := before.Uuid
    qs := "UPDATE users SET "
    changes := make(map[string]interface{}, 0)
    newUser := &pb.User{
        Uuid: uuid,
        Generation: before.Generation + 1,
    }
    if changed.DisplayName != nil {
        newDisplayName := changed.DisplayName.Value
        newSlug := slug.Make(newDisplayName)
        changes["display_name"] = newDisplayName
        newUser.DisplayName = newDisplayName
        newUser.Slug = newSlug
    } else {
        newUser.DisplayName = before.DisplayName
        newUser.Slug = before.Slug
    }
    if changed.Email != nil {
        newEmail := changed.Email.Value
        changes["email"] = newEmail
        newUser.Email = newEmail
    } else {
        newUser.Email = before.Email
    }
    for field, _ := range changes {
        qs = qs + fmt.Sprintf("%s = ?, ", field)
    }
    // Trim off the last comma and space
    qs = qs[0:len(qs)-2]

    qs = qs + " WHERE uuid = ? AND generation = ?"

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
    return newUser, nil
}

// Returns the organizations a user belongs to
func (s *Storage) UserMembersList(
    req *pb.UserMembersListRequest,
) (*sql.Rows, error) {
    reset := s.log.WithSection("iam/storage")
    defer reset()
    // First verify the supplied user exists
    search := req.User
    userId := s.userIdFromIdentifier(search)
    if userId == 0 {
        notFound := fmt.Errorf("No such user found.")
        return nil, notFound
    }
    qs := `
SELECT
  o.uuid
, o.display_name
, o.slug
, o.generation
, po.uuid
FROM organization_users AS ou
JOIN organizations AS o
 ON ou.organization_id = o.id
LEFT JOIN organizations AS po
 ON o.parent_organization_id = po.id
WHERE ou.user_id = ?
`
    rows, err := s.db.Query(qs, userId)
    if err != nil {
        return nil, err
    }
    err = rows.Err()
    if err != nil {
        return nil, err
    }
    return rows, nil
}
