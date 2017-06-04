#!/usr/bin/env bash

set -o nounset

ROOTDIR="$(readlink -f $(dirname $(dirname $0)))"
E2EDIR="$ROOTDIR/e2e"
LIBDIR="$E2EDIR/lib"
ERRLOG=$E2EDIR/err.log

truncate -s 0 $ERRLOG

if [ -f $ROOTDIR/.processionrc ] ; then
    source $ROOTDIR/.processionrc
fi

num_tests_run=0
num_tests_passed=0
num_tests_skipped=0
num_tests_failed=0
total_time_elapsed="0 seconds"

echo "Running end to end functional integration tests for Procession..."
echo ""
echo "Configuration:"
echo "------------------------------------------------------------------------"
echo "Root dir:              $ROOTDIR"
echo "Run on:                $(date -u)"
echo "Git SHA:               $(git describe --tags --always --dirty)"
echo "PROCESSION_USER:       ${PROCESSION_USER:-}"
echo "PROCESSION_LOG_LEVEL:  ${PROCESSION_LOG_LEVEL:-}"
echo "GSR_ETCD_ENDPOINTS:    ${GSR_ETCD_ENDPOINTS:-}"
echo "GSR_LOG_LEVEL:         ${GSR_LOG_LEVEL:-}"
echo "------------------------------------------------------------------------"
echo "Starting tests ..."


for t in ping_endpoints; do
    printf "    %-63s "  "$t ..."
    . $E2EDIR/tests/$t
    rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "  ok"
        num_tests_passed=$(( $num_tests_passed + 1 ))
    elif [[ $rc -eq 1 ]]; then
        echo "fail"
        num_tests_failed=$(( $num_tests_failed + 1 ))
    else
        echo "skip"
        num_tests_skipped=$(( $num_tests_skipped + 1 ))
    fi
done

echo "------------------------------------------------------------------------"
echo "Completed $num_tests_run tests in $total_time_elapsed"
echo "Passed:   $num_tests_passed"
echo "Skipped:  $num_tests_skipped"
echo "Failed:   $num_tests_failed"

if [[ $num_tests_failed -gt 0 ]]; then
    echo "Errors in $ERRLOG:"
    cat $ERRLOG
fi

exit $num_tests_failed
