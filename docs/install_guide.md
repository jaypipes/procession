# Installation Guide


## Configuring the IAM database

By default, the IAM system uses a MySQL database for storing user, role, and
organization information. This database needs to be created and the database
schema brought up to the latest version.

### Creating a new IAM database

To create a new database in MySQL, issue the following command:

```
$ mysql -u$DBUSER -p -e "CREATE DATABASE IF NOT EXISTS $DBNAME"
```

where `$DBUSER` is a MySQL user with the ability to create a new schema and
`$DBNAME` is the name of the Procession IAM database.

### Syncing the IAM database schema

Once the IAM database has been created, bring the database schema up to date
with the latest schema by using the `goose` program from the installation
source directory:

```
$ goose -dir migrate/iam mysql "$DBUSER:$DBPASSWORD@/$DBNAME" up
```

Where `$DBPASSWORD` is the password for the MySQL user `$DBUSER`.

**TODO(jaypipes)**: Make this step more user-friendly and automated with a
script.

## Bootstrapping

Before a Procession system is fully operational, you will need to create one or
more user accounts that have the `SUPER` permission. The `SUPER` permission, as
the name implies, allows the user to perform any action in the system.

After configuring your IAM database but before bootstrapping, if you attempt to
perform an action against the Procession system, you will get an authorization
failure similar to the following:

```
$ p7n --user user@company.com organization list
Error: rpc error: code = Unknown desc = User is not authorized to perform that action
rpc error: code = Unknown desc = User is not authorized to perform that action
```

To bootstrap the Procession system, you use the `p7n bootstrap` command,
supplying one or more email addresses for user accounts that will be associated
with a role that contains the `SUPER` permission:

```
$ p7n bootstrap --key 12345 --super-user-email user@company.com
OK
```

The `--key` needs to match the value of the `--bootstrap-key` CLI option used
when starting the Procession IAM service. When a bootstrap operation succeeds,
the bootstrap key is deleted for safety, so the same key cannot be used to
bootstrap again:

```
$ p7n bootstrap --key 12345 --super-user-email user@company.com 
Error: rpc error: code = Unknown desc = Invalid bootstrap key
```
