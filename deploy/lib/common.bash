#!/usr/bin/env bash

check_is_installed() {
    local name="$1"
    if [[ ! `which $name` ]]; then
        echo "Please install $name before runing this script. Check docs/developing.md for more information."
        exit 1
    fi
}

debug_enabled() {
    if [[ $DEBUG != 0 ]]; then
        return 0
    else
        return 1
    fi
}
