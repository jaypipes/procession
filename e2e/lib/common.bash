#!/usr/bin/env bash

check_is_installed() {
    local name="$1"
    if [[ ! `which $name` ]]; then
        echo "Please install $name before runing this script. Check docs/developing.md for more information."
        exit 1
    fi
}

errlog() {
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
