#!/usr/bin/env bash

set -e

DEBUG=${DEBUG:-0}
ROOT_DIR=$(cd $(dirname "$0")/.. && pwd)
VENDOR_DIR=$ROOT_DIR/vendor
SCRIPTS_DIR=$ROOT_DIR/scripts
LIB_DIR=$SCRIPTS_DIR/lib

source $LIB_DIR/common.bash

check_is_installed govendor

if debug_enabled; then
    set -o xtrace
fi

ENSURE="$1"

if [[ $ENSURE == "--ensure" ]]; then
    # The --ensure option only pulls in vendored code packages using govendor
    # sync +m if vendored code has not already been pulled down. We check here
    # for a known vendored repository to see if vendored code has already been
    # pulled.
    if [[ -e $VENDOR_DIR/golang.org/x/net/context/context.go ]]; then
        exit 0
    fi
fi

govendor sync +m
