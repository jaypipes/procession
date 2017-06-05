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
