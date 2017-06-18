#!/usr/bin/env bash

check_is_installed() {
    local name="$1"
    if [[ ! `which $name` ]]; then
        echo "Please install $name before running this script. Check docs/developing.md for more information."
        exit 1
    fi
}

elog() {
    local testname="$1"
    local testout="$2"

    echo "" >> $ERRLOG
    echo "===== BEGIN $testname ==============================" >> $ERRLOG
    echo "" >> $ERRLOG
    echo "$testout" >> $ERRLOG
    echo "" >> $ERRLOG
    echo "===== END $testname ================================" >> $ERRLOG
    echo "" >> $ERRLOG
}

rlog() {
    echo $1
    echo $1 >> $RUNLOG
}

rlogf() {
    printf "$1" "$2"
    printf "$1" "$2" >> $RUNLOG
}

olog() {
    echo $1
    echo $1 >> $OUTLOG
}

ologf() {
    printf "$1" "$2"
    printf "$1" "$2" >> $OUTLOG
}

reset_database() {
    echo -n "Checking if e2e testing database exists ... "
    dbname=${PROCESSION_TESTING_E2E_DB_NAME:-procession_testing_e2e}
    dbuser=${PROCESSION_TESTING_E2E_DB_ADMIN_USER:-root}
    dbpass=${PROCESSION_TESTING_E2E_DB_ADMIN_USER_PASSWORD:-}
    conn="$dbuser:$dbpass@/$dbname"
    if [[ ! $(mysql -u"$dbuser" -N -p$dbpass -e "SHOW DATABASES LIKE '$dbname'" 2>/dev/null | grep "$dbname") ]]; then
        echo "no."
    else
        echo "yes."
        echo -n "Removing e2e testing database ... "
        mysql -u"$dbuser" -p$dbpass -e "DROP SCHEMA $dbname" 2>/dev/null
        echo "done."
    fi

    echo -n "Creating new e2e testing database ... "
    mysql -u"$dbuser" -p$dbpass -e "CREATE SCHEMA $dbname" 2>/dev/null
    echo "done."

    echo "Bringing database up to latest schema version ... "
    goose -dir $ROOT_DIR/migrate/iam mysql $conn  up
}
