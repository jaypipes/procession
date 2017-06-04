#!/usr/bin/env bash

set -o nounset

ROOT_DIR="$(readlink -f $(dirname $(dirname $0)))"
BIN_DIR="$ROOT_DIR/build/bin"
E2E_DIR="$ROOT_DIR/e2e"
TESTS_DIR="$E2E_DIR/tests"
LIB_DIR="$E2E_DIR/lib"
RUNLOG=$E2E_DIR/run.log
ERRLOG=$E2E_DIR/err.log

truncate -s 0 $ERRLOG
truncate -s 0 $RUNLOG

if [ -f $ROOT_DIR/.processionrc ] ; then
    source $ROOT_DIR/.processionrc
fi

source $LIB_DIR/common.bash

P7N="$BIN_DIR/p7n"

num_tests_run=0
num_tests_passed=0
num_tests_skipped=0
num_tests_failed=0
total_time_elapsed="0 seconds"

echo "Running end to end functional integration tests for Procession..."
echo ""
rlog "Configuration:"
rlog "------------------------------------------------------------------------"
rlog "Root dir:              $ROOT_DIR"
rlog "Run on:                $(date -u)"
rlog "Git SHA:               $(git describe --tags --always --dirty)"
rlog "PROCESSION_USER:       ${PROCESSION_USER:-}"
rlog "PROCESSION_LOG_LEVEL:  ${PROCESSION_LOG_LEVEL:-}"
rlog "GSR_ETCD_ENDPOINTS:    ${GSR_ETCD_ENDPOINTS:-}"
rlog "GSR_LOG_LEVEL:         ${GSR_LOG_LEVEL:-}"
rlog "------------------------------------------------------------------------"
echo "Starting tests ..."


for t in $TESTS_DIR/*; do
    tname=$( basename $t )
    rlogf "    %-63s "  "$tname ..."
    . $t
    rc=$?
    if [[ $rc -eq 0 ]]; then
        rlog "  ok"
        num_tests_passed=$(( $num_tests_passed + 1 ))
    elif [[ $rc -eq 1 ]]; then
        rlog "fail"
        num_tests_failed=$(( $num_tests_failed + 1 ))
    else
        rlog "skip"
        num_tests_skipped=$(( $num_tests_skipped + 1 ))
    fi
done

rlog "------------------------------------------------------------------------"
rlog "Completed $num_tests_run tests in $total_time_elapsed"
rlog "Passed:   $num_tests_passed"
rlog "Skipped:  $num_tests_skipped"
rlog "Failed:   $num_tests_failed"

if [[ $num_tests_failed -gt 0 ]]; then
    echo "Errors in $ERRLOG:"
    cat $ERRLOG
fi

exit $num_tests_failed
