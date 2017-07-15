# User Guide

## Identity and account management

There are a number of concepts involved in the authentication, authorization
and account management features of Procession. In this section, we describe
these concepts.

A **user** is an identity that is used to log in to a Procession system and
perform an action. Users can create repositories, push changesets,
review other's changesets and create new organizations.

An **organization** is a collection of users. Organizations can have child
organizations. An organization can own one or more repositories.

### Managing users

A new user can be added to the system using the `p7n user create` command.
Supply an email and a display name for the user, and Procession will return the
newly-created user's UUID and "slug", which is an easy-to-remember string that
you can use to identify the user:

```
$ p7n user create --display-name "Fred Flintstone" --email "fred@flintstone.com"
Successfully created user with UUID af9e54ee75a2a9f611e7372c21e8d0a8
UUID:         af9e54ee75a2a9f611e7372c21e8d0a8
Display name: Fred Flintstone
Email:        fred@flintstone.com
Slug:         fred-flintstone
```

**Note**: You can silence the outputting of all but the newly-created user's
UUID by using the `--quiet` option.

To retrieve information about a specific user, the `p7n user get <search>`
command can be run, specifying a user's UUID, display name, slug or email as
the `<search>` string:

```
$ p7n user get fred-flintstone
UUID:         af9e54ee75a2a9f611e7372c21e8d0a8
Display name: Fred Flintstone
Email:        fred@flintstone.com
Slug:         fred-flintstone

$ p7n user get af9e54ee75a2a9f611e7372c21e8d0a8
UUID:         af9e54ee75a2a9f611e7372c21e8d0a8
Display name: Fred Flintstone
Email:        fred@flintstone.com
Slug:         fred-flintstone
```

You may edit the user's information using the `p7n user update <search>`
command, supplying the user's UUID, email, display name or slug as the
`<search>` string:

```
$ p7n user update af9e54ee75a2a9f611e7372c21e8d0a8 --email "fflintstone@yabbadabba.com"
Successfully saved user <af9e54ee75a2a9f611e7372c21e8d0a8>

$ p7n user get af9e54ee75a2a9f611e7372c21e8d0a8
UUID:         af9e54ee75a2a9f611e7372c21e8d0a8
Display name: Fred Flintstone
Email:        fflintstone@yabbadabba.com
Slug:         fred-flintstone
```

To show a tabular view of zero or more users, call the `p7n user list` command:

```
$ p7n user list
+----------------------------------+-----------------+----------------------------+-----------------+
|               UUID               |  DISPLAY NAME   |           EMAIL            |      SLUG       |
+----------------------------------+-----------------+----------------------------+-----------------+
| af9e54ee75a2a9f611e7372c21e8d0a8 | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
| 8509e0699503483711e73802066a89c6 | Speedy Gonzalez | speedy@gonzalez.com        | speedy-gonzalez |
+----------------------------------+-----------------+----------------------------+-----------------+
```

You can search for users with specific emails, display names, UUIDs, or slugs
by supplying a comma-delimited list of things to search for, as these examples
show:

```
$ go run p7n/main.go user list --slug fred-flintstone
+----------------------------------+-----------------+----------------------------+-----------------+
|               UUID               |  DISPLAY NAME   |           EMAIL            |      SLUG       |
+----------------------------------+-----------------+----------------------------+-----------------+
| af9e54ee75a2a9f611e7372c21e8d0a8 | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
+----------------------------------+-----------------+----------------------------+-----------------+
```

```
$ p7n user list --email fflintstone@yabbadabba.com,speedy@gonzalez.com
+----------------------------------+-----------------+----------------------------+-----------------+
|               UUID               |  DISPLAY NAME   |           EMAIL            |      SLUG       |
+----------------------------------+-----------------+----------------------------+-----------------+
| af9e54ee75a2a9f611e7372c21e8d0a8 | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
| 8509e0699503483711e73802066a89c6 | Speedy Gonzalez | speedy@gonzalez.com        | speedy-gonzalez |
+----------------------------------+-----------------+----------------------------+-----------------+
```

**NOTE**: When running any `p7n` command, you will only see records that you
are allowed to view based on your access and permissions. See the
"Authorization concepts" section below for more details.

To delete a user, use the `p7n user delete <user>` command, supplying a user's
slug, email or UUID:

```
$ p7n user get betty-rubble
UUID:         1f5627c4797f404485005982edf84354
Display name: Betty Rubble
Email:        betty@rubble.com
Slug:         betty-rubble

$ p7n user delete betty-rubble
Successfully deleted user betty-rubble
```

**Note**: Deleting a user will delete all the user's memberships in any
organizations and any resources owned by the user. If a user is deleted and the
user was the sole member of an organization, that organization and its
resources are also deleted.

### Viewing a user's memberships

A user can be a member in one or more organizations. To view the organizations
a user is a member of, use the `p7n user members <user>` command, as the
following example shows:

```
$ p7n user list
+----------------------------------+------------------+----------------------+------------------+
|               UUID               |   DISPLAY NAME   |        EMAIL         |       SLUG       |
+----------------------------------+------------------+----------------------+------------------+
| ab849d069c354ce6b182a01a36a336d5 | Fred Flintstone  | fred@flintstone.com  | fred-flintstone  |
| 2190c3c936534f9eb676d3becc456d86 | Wilma Flintstone | wilma@flintstone.com | wilma-flintstone |
| 97f1264f966943ef9f88ac0a00adabc2 | Barney Rubble    | barney@rubble.com    | barney-rubble    |
| 5aa80e24ab2f482b9316724a7e0efbbb | Homer Simpson    | homer@simpson.com    | homer-simpson    |
| d2d2ec3d4b4045368014d9a9228d95b0 | Marge Simpson    | marge@simpson.com    | marge-simpson    |
| 06bb089a22b74342bc5beb6e90a2e7ef | Bart Simpson     | bart@simpson.com     | bart-simpson     |
| 57f9946b6b234caea9fbc69ee8967515 | Admin            | admin@procession.com | admin            |
+----------------------------------+------------------+----------------------+------------------+

$ p7n organization list --tree
── Cartoons (263e6988403a4867994c09ec6d651dff)
   └── The Flintstones (0f1bae2ea2014bda97b156e3ed5e74aa)
       └── Husbands (0778001a33844a849636bd98a898ab32)
       └── Wives (73e1f433825a480c87bbc11861392848)
   └── The Simpsons (a8681d3f26c84c65afaae381254dbe9a)
       └── Boys (6d9f63b010154b0abe3270c4f936216c)
       └── Girls (a39367c81b1641678ff74546f4539e53)

$ p7n user members ab849d069c354ce6b182a01a36a336d5
+----------------------------------+--------------+----------+----------------------------------+
|               UUID               | DISPLAY NAME |   SLUG   |              PARENT              |
+----------------------------------+--------------+----------+----------------------------------+
| 0778001a33844a849636bd98a898ab32 | Husbands     | husbands | 0f1bae2ea2014bda97b156e3ed5e74aa |
+----------------------------------+--------------+----------+----------------------------------+

$ p7n user members 57f9946b6b234caea9fbc69ee8967515
+----------------------------------+--------------+----------+--------+
|               UUID               | DISPLAY NAME |   SLUG   | PARENT |
+----------------------------------+--------------+----------+--------+
| 263e6988403a4867994c09ec6d651dff | Cartoons     | cartoons |        |
+----------------------------------+--------------+----------+--------+
```

### Managing organizations

A new organization can be added to the system using the `p7n organization
create` command. Supply a display name for the organization, and Procession
will return the newly-created organization's UUID and "slug", which is an
easy-to-remember string that you can use to identify the organization:

```
$ p7n organization create --display-name "Cartoons"
Successfully created organization with UUID 3f09849ba1724eac9e77687495dab9f4
UUID:         3f09849ba1724eac9e77687495dab9f4
Display name: Cartoons
Slug:         cartoons
```

**Note**: You can silence the outputting of all but the newly-created
organization's UUID by using the `--quiet` option.

If you want to make your new organization a child (or suborganization) of
another, pass the name, slug or UUID of the parent organization using the
`--parent` CLI option:

```
$ p7n organization create --display-name "Flintstones" --parent cartoons
Successfully created organization with UUID 
UUID:         0c687720d96446738dc3dbf661f87c55
Display name: Flintstones
Slug:         flintstones
Parent:       Cartoons [3f09849ba1724eac9e77687495dab9f4]
```

To retrieve information about a specific organization, the `p7n organization
get <search>` command can be run, specifying an organization's UUID, display
name, or slug as the `<search>` string:

```
$ p7n organization get 3f09849ba1724eac9e77687495dab9f4
UUID:         3f09849ba1724eac9e77687495dab9f4
Display name: Cartoons
Slug:         cartoons

$ p7n organization get cartoons
UUID:         3f09849ba1724eac9e77687495dab9f4
Display name: Cartoons
Slug:         cartoons
```

You may edit the organization's information using the `p7n organization update
<search>` command, supplying the organization's UUID, display name or slug as
the `<search>` string:

```
$ p7n organization update 3f09849ba1724eac9e77687495dab9f4 --display-name "The Flintstones"
Successfully saved organization 3f09849ba1724eac9e77687495dab9f4
UUID:         3f09849ba1724eac9e77687495dab9f4
Display name: The Flintstones
Slug:         the-flintstones
```

To show a tabular view of zero or more organizations, call the `p7n organization list` command:

```
$ p7n organization list
+----------------------------------+----------------+-----------------+----------+
|               UUID               |  DISPLAY NAME  |      SLUG       |  PARENT  |
+----------------------------------+----------------+-----------------+----------+
| 10b4e38038c911e7940fe06995034837 | Cartoons       | cartoons        |          |
| 3f09849ba1724eac9e77687495dab9f4 | The Flintstones| the-flintstones | Cartoons |
+----------------------------------+----------------+-----------------+----------+
```

You can search for organizations with specific display names, UUIDs, or slugs
by supplying a comma-delimited list of things to search for, as these examples
show:

```
$ p7n organization list --uuid 10b4e38038c911e7940fe06995034837
+----------------------------------+--------------+----------+--------+
|               UUID               | DISPLAY NAME |   SLUG   | PARENT |
+----------------------------------+----------------+--------+--------+
| 10b4e38038c911e7940fe06995034837 | Cartoons     | cartoons |        |
+----------------------------------+--------------+----------+--------+

$ p7n organization list --slug the-flintstones,cartoons
+----------------------------------+----------------+-----------------+----------+
|               UUID               |  DISPLAY NAME  |      SLUG       |  PARENT  |
+----------------------------------+----------------+-----------------+----------+
| 10b4e38038c911e7940fe06995034837 | Cartoons       | cartoons        |          |
| 3f09849ba1724eac9e77687495dab9f4 | The Flintstones| the-flintstones | Cartoons |
+----------------------------------+----------------+-----------------+----------+
```

You can supply the `--tree` (`-t`) CLI option to the `p7n organization list`
command to see a tree-view of the organizations matching any filters:

```
$ p7n organization list --tree
── A (d282791a50444b069c6ff7f0e8781211)
   └── C (f1f1584b641042c19de9e333feabeaa4)
       └── C.2 (7cee11944528412991dd785dde90fcab)
       └── C.1 (5558861719ca43d4978427826f0a4404)
           └── C.1.a (82ba2cc190b541b4928ec7128d4f893e)
       └── C.3 (ea61661cc4ae4a51b9b8c95967ead432)
   └── B (f72370fe01cd43f89c1ffd54a2b83295)
```

To delete an organization, use the `p7n organization delete <organization>`
command, supplying an organization's slug or UUID:

```
$ p7n organization delete a0c5b0a68c724aadba620bfa6c4f1544
Successfully deleted organization a0c5b0a68c724aadba620bfa6c4f1544
```

**Note**: Deleting an organization will delete all child organizations, all
membership records in that organization, and all resources owned by the
organization.

### Managing an organization's membership

An organization is composed of one or more users. These users comprise the
organization's **membership**. To see a list of users belonging to an
organization, use the `p7n organization members <organization>` command, like
so:

```
$ p7n organization members flintstones
+----------------------------------+---------------+-------------------+---------------+
|               UUID               | DISPLAY NAME  |       EMAIL       |     SLUG      |
+----------------------------------+---------------+-------------------+---------------+
| f1312f3ac70a421982ae91573b66ea9e | Barney Rubble | barney@rubble.com | barney-rubble |
+----------------------------------+---------------+-------------------+---------------+
```

**Note**: When creating a new organization, the user who created the
organization is automatically added to the organization's membership. There
must always be at least one user who is a member of an organization.

To add a new user to an organization's membership, use the same `p7n organization
members <organization>` command, with an additional "add" CLI argument followed
by a comma-separated list of user identifiers. User identifiers can be an
email, a UUID, display name or slug:

```
$ p7n organization members flintstones add fred-flintstone,wilma@flintstone.com
OK

$ p7n organization members flintstones
+----------------------------------+-------------------+----------------------+------------------+
|               UUID               |   DISPLAY NAME    |        EMAIL         |       SLUG       |
+----------------------------------+-------------------+----------------------+------------------+
| c6d49a59382f478492cd942cecbc1b1c | Freddy Flintstone | fred@flintstone.com  | fred-flintstone  |
| f1312f3ac70a421982ae91573b66ea9e | Barney Rubble     | barney@rubble.com    | barney-rubble    |
| c7fd02a5cc3e4d82b2ad705100d67664 | Wilma Flintstone  | wilma@flintstone.com | wilma-flintstone |
+----------------------------------+-------------------+----------------------+------------------+

```

## Authorization concepts

Whether or not a user is allowed to perform some action or access some resource
in Procession is determined by examining the set of **permissions** the user
has and the context within which the user has made a request.

Permissions are deduced by examining the **roles** that a user has. Each role
has a set of permissions granted to it.

### Viewing permissions

To see the list of permissions, use the `p7n permissions` command:

```
$ p7n permissions
+---------------------+
|     PERMISSION      |
+---------------------+
| CREATE_ANY          |
| CREATE_CHANGE       |
       ...
| READ_REPO           |
| READ_USER           |
| SUPER               |
+---------------------+
```

### Managing Roles

Roles are simply a collection of permissions. If a role is associated with a
specific organization, the permissions apply **only** to the objects and
resources within that organization.

To view a list of roles, use the `p7n role list` command, specifying a display
name for the role, an optional organization identifier (name, slug, or UUID)
and an optional set of granted permissions for the role.

The following example creates a new role called "repo-admins" that gives any
user who is assigned to that role the ability to perform any action against any
repo:

```
$ p7n role create --display-name "Repo Admins" --permissions CREATE_REPO,DELETE_REPO,MODIFY_REPO,READ_ANY
Successfully created role with UUID 999733afb28c426db8511b3a1d88d834
UUID:         999733afb28c426db8511b3a1d88d834
Display name: Repo Admins
Slug:         repo-admins
Permissions:  CREATE_REPO, DELETE_REPO, MODIFY_REPO, READ_ANY
```

**Note**: You can silence the outputting of all but the newly-created role's
UUID by using the `--quiet` option.

This next example creates a new role within the "Heroes" organization that
allows any user who is assigned to the role the ability to read any object or
resource owned by the "Heroes" organization. Note the use of the
`--organization` CLI option to scope the role to a particular organization.

```
$ /p7n role create --display-name "Readers" --organization heroes --permissions READ_ANY
Successfully created role with UUID 560fdab66e8e4bdf98ab43f81dc9cee3
UUID:         560fdab66e8e4bdf98ab43f81dc9cee3
Organization: Heroes [b3462d857efa472e803152204ba32a42]
Display name: Readers
Slug:         heroes-readers
Permissions:  READ_ANY
```

**Note**: You will notice that the slug generated for the new role is a
combination of the supplied display name and the organization's slug. This
practice allows us to enforce unique role names within an organization as well
as globally.

To view a list of all roles, use the `p7n role list` command:

```
p7n role list
+----------------------------------+--------------+----------------+--------------+
|               UUID               | DISPLAY NAME |      SLUG      | ORGANIZATION |
+----------------------------------+--------------+----------------+--------------+
| 37033fe0861842528dae6caa235f2346 | admins       | admins         |              |
| 92c3bed3f4604eb5ae418c5ac05009ca | default      | default        |              |
| 999733afb28c426db8511b3a1d88d834 | Repo Admins  | repo-admins    |              |
| 560fdab66e8e4bdf98ab43f81dc9cee3 | Readers      | heroes-readers | Heroes       |
+----------------------------------+--------------+----------------+--------------+
```

You can filter the results of the command by specifying one or more names,
slugs or UUIDs, as in these examples:

```
$ p7n role list --uuid 92c3bed3f4604eb5ae418c5ac05009ca
+----------------------------------+--------------+---------+--------------+
|               UUID               | DISPLAY NAME |  SLUG   | ORGANIZATION |
+----------------------------------+--------------+---------+--------------+
| 92c3bed3f4604eb5ae418c5ac05009ca | default      | default |              |
+----------------------------------+--------------+---------+--------------+

$ p7n role list --slug admins
+----------------------------------+--------------+--------+--------------+
|               UUID               | DISPLAY NAME |  SLUG  | ORGANIZATION |
+----------------------------------+--------------+--------+--------------+
| 37033fe0861842528dae6caa235f2346 | admins       | admins |              |
+----------------------------------+--------------+--------+--------------+

$ p7n role list --display-name Readers,Admins
+----------------------------------+--------------+----------------+--------------+
|               UUID               | DISPLAY NAME |      SLUG      | ORGANIZATION |
+----------------------------------+--------------+----------------+--------------+
| 37033fe0861842528dae6caa235f2346 | admins       | admins         |              |
| 560fdab66e8e4bdf98ab43f81dc9cee3 | Readers      | heroes-readers | Heroes       |
+----------------------------------+--------------+----------------+--------------+
```

You may also filter by organization identifier, as this example shows:

```
$ p7n role list
+----------------------------------+--------------+----------------+--------------+
|               UUID               | DISPLAY NAME |      SLUG      | ORGANIZATION |
+----------------------------------+--------------+----------------+--------------+
| 560fdab66e8e4bdf98ab43f81dc9cee3 | Readers      | heroes-readers | Heroes       |
| 37033fe0861842528dae6caa235f2346 | admins       | admins         |              |
| 92c3bed3f4604eb5ae418c5ac05009ca | default      | default        |              |
+----------------------------------+--------------+----------------+--------------+

$ p7n role list --organization heroes
+----------------------------------+--------------+----------------+--------------+
|               UUID               | DISPLAY NAME |      SLUG      | ORGANIZATION |
+----------------------------------+--------------+----------------+--------------+
| 560fdab66e8e4bdf98ab43f81dc9cee3 | Readers      | heroes-readers | Heroes       |
+----------------------------------+--------------+----------------+--------------+
$ p7n role list --organization villains
No records found matching search criteria.
```

To view information about a specific role, use the `p7n role get <ROLE>`
command, supplying a UUID, display name or slug identifier:

```
$ p7n role get 560fdab66e8e4bdf98ab43f81dc9cee3
UUID:         560fdab66e8e4bdf98ab43f81dc9cee3
Organization: Heroes [b3462d857efa472e803152204ba32a42]
Display name: Readers
Slug:         heroes-readers
Permissions:  READ_ANY

$ p7n role get Admins
UUID:         37033fe0861842528dae6caa235f2346
Display name: admins
Slug:         admins
Permissions:  SUPER
```

To modify an existing role, use the `p7n role update <ROLE>` command. You can
add and remove permissions from the role as well as change the name of the
role, as these examples show:


```
p7n role update Admins --display-name Adminstrators
Successfully saved role 37033fe0861842528dae6caa235f2346
UUID:         37033fe0861842528dae6caa235f2346
Display name: Adminstrators
Slug:         adminstrators
Permissions:  SUPER

$ p7n role get repo-admins
UUID:         999733afb28c426db8511b3a1d88d834
Display name: Repo Admins
Slug:         repo-admins
Permissions:  READ_ANY, CREATE_REPO, MODIFY_REPO, DELETE_REPO

$ p7n role update repo-admins --remove READ_ANY
Successfully saved role 999733afb28c426db8511b3a1d88d834
UUID:         999733afb28c426db8511b3a1d88d834
Display name: Repo Admins
Slug:         repo-admins
Permissions:  DELETE_REPO, CREATE_REPO, MODIFY_REPO
```

To delete a role, use the `p7n role delete <ROLE>` command:

```
$ p7n role delete repo-admins
Successfully deleted role repo-admins
```

This will delete the role and any user-role assignments for that role.

**Note**: You can silence the success message output by using the `--quiet`
option.

### Assigning roles to a user

As mentioned above, the ability of a user to perform actions within the
Procession system is determined by the roles that user has.

To view the roles a user has assigned to them, use the `p7n user roles <USER>`
command:

```
$ p7n user roles superman
+----------------------------------+--------------+----------------+--------------+
|               UUID               | DISPLAY NAME |      SLUG      | ORGANIZATION |
+----------------------------------+--------------+----------------+--------------+
| 560fdab66e8e4bdf98ab43f81dc9cee3 | Readers      | heroes-readers | Heroes       |
+----------------------------------+--------------+----------------+--------------+
```

The same command can be used to add and remove roles from a user:

```
$ p7n user roles superman add admins remove readers
OK

$ p7n user roles superman
+----------------------------------+--------------+--------+--------------+
|               UUID               | DISPLAY NAME |  SLUG  | ORGANIZATION |
+----------------------------------+--------------+--------+--------------+
| 37033fe0861842528dae6caa235f2346 | admins       | admins |              |
+----------------------------------+--------------+--------+--------------+
```
