# Upgrading

## Database migrations

Procession components that use a database have corresponding database migration
tools that upgrade database schemas and perform any needed data migrations.

### Install `goose`

We use the `github.com/pressly/goose/cmd/goose` tool to run database
migrations. To use it, install `goose` on a machine that has access to the
databases you need to upgrade:

```
go get -u github.com/pressly/goose/cmd/goose
```

### Applying database migrations

Use `goose up` to bring a particular database up to its latest version, specify
the user/password, the database name, and supply the appropriate directory
under the [/migrate](../migrate) directory. For example:

```
jaypipes@uberbox:~/src/github.com/jaypipes/procession$ goose -dir migrate/iam/  mysql "jaypipes:$PASSWORD@/procession_iam" up
OK    20170425235023_init.sql
```
