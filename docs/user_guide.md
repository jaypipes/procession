# User Guide

### Organization

## Identity and account management

There are a number of concepts involved in the authentication, authorization
and account management features of Procession. In this section, we describe
these concepts.

A **user** is an identity that is used to log in to a Procession system and
perform an action.

An **organization** is a collection of users.

### User management

A new user can be added to the system using the `p7n user set` command. Supply
an email and a display name for the user, and Procession will return the
newly-created user's UUID and "slug", which is an easy-to-remember string that
you can use to identify the user:

```
$ p7n user set --display-name "Fred Flintstone" --email "fred@flintstone.com"
Successfully created user with UUID af9e54ee75a2a9f611e7372c21e8d0a8
UUID:         af9e54ee75a2a9f611e7372c21e8d0a8
Display name: Fred Flintstone
Email:        fred@flintstone.com
Slug:         fred-flintstone
```

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

You may edit the user's information using the same `p7n user set <search>`
command, supplying the user's UUID, email, display name or slug as the
`<search>` string:

```
$ p7n user set af9e54ee75a2a9f611e7372c21e8d0a8 --email "fflintstone@yabbadabba.com"
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
| 8509e0699503483711e73801f5478d3a | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
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
| 8509e0699503483711e73801f5478d3a | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
+----------------------------------+-----------------+----------------------------+-----------------+
```

```
$ p7n user list --email fflintstone@yabbadabba.com,speedy@gonzalez.com
+----------------------------------+-----------------+----------------------------+-----------------+
|               UUID               |  DISPLAY NAME   |           EMAIL            |      SLUG       |
+----------------------------------+-----------------+----------------------------+-----------------+
| 8509e0699503483711e73801f5478d3a | Fred Flintstone | fflintstone@yabbadabba.com | fred-flintstone |
| 8509e0699503483711e73802066a89c6 | Speedy Gonzalez | speedy@gonzalez.com        | speedy-gonzalez |
+----------------------------------+-----------------+----------------------------+-----------------+
```

## Authorization concepts

Whether or not a user is allowed to perform some action or access some resource
in Procession is determined by examining the set of **permissions** the user
has and the context within which the user has made a request.
