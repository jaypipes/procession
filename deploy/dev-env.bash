#!/usr/bin/env bash

set -e

DEBUG=${DEBUG:-0}
ROOT_DIR=$(cd $(dirname "$0")/.. && pwd)
DEPLOY_DIR=$ROOT_DIR/deploy
SCRIPTS_DIR=$ROOT_DIR/scripts
LIB_DIR=$SCRIPTS_DIR/lib
RCFILE=${PROCESSION_TESTING_RCFILE:-.processionrc}

source $LIB_DIR/common.bash

check_is_installed rkt

if debug_enabled; then
    set -o xtrace
fi

if debug_enabled; then
    echo "================= DEBUG ==============="
    systemctl --version
    rkt version
    echo "======================================="
fi

if [ -f $ROOT_DIR/$RCFILE ] ; then
    echo "Found $RCFILE file. Sourcing."
    source $ROOT_DIR/$RCFILE
fi

if debug_enabled; then
    # Override the log levels in sourced .processionrc to be as high as
    # possible
    export GSR_LOG_LEVEL=3
    export PROCESSION_LOG_LEVEL=3
fi

NODE_ADDRESS=${NODE_ADDRESS:-localhost}

echo -n "Checking if etcd3 is already running ... "
PROCESSION_TEST_ETCD_HOST=$(sudo rkt list --no-legend | grep etcd | grep running | cut -f7 | cut -d'=' -f2)
if [[ "$PROCESSION_TEST_ETCD_HOST" != "" ]]; then
    echo "yes (at $PROCESSION_TEST_ETCD_HOST)."
else
    echo "no."

    echo -n "Checking if an old rkt etcd3 pod is inactive ... "
    EXITED_ETCD_POD=$( sudo rkt list --no-legend | grep etcd | grep 'exited' | cut -f1 )
    if [[ "$EXITED_ETCD_POD" != "" ]]; then
        echo "yes."
        echo -n "Shutting down pod $EXITED_ETCD_POD ... "
        sudo rkt rm $EXITED_ETCD_POD >/dev/null 2>&1
        sleep 1
        echo "ok."
    else
        echo "no."
    fi

    echo -n "Checking and installing ACI keys for etcd ... "
    sudo rkt trust --prefix=coreos.com/etcd --skip-fingerprint-review >/dev/null 2>&1
    echo "ok."

    echo -n "Starting etcd3 rkt pod ... "
    sudo systemd-run --slice=machine \
        --description=testing-procession-etcd3 \
        --unit=testing-procession-etcd3 \
        rkt run coreos.com/etcd:v3.0.6 -- \
        -name=processiontest -advertise-client-urls=http://${NODE_ADDRESS}:2379 \
        -initial-advertise-peer-urls=http://${NODE_ADDRESS}:2380 \
        -listen-client-urls=http://0.0.0.0:2379 \
        -listen-peer-urls=http://${NODE_ADDRESS}:2380 \
        -initial-cluster=processiontest=http://${NODE_ADDRESS}:2380 >/dev/null 2>&1
    echo "ok."

    echo -n "Determining etcd3 endpoint address ... "

    sleep_time=0

    PROCESSION_TEST_ETCD_HOST=""
    until [ $sleep_time -eq 8 ]; do
        sleep $(( sleep_time++ ))
        PROCESSION_TEST_ETCD_HOST=$(sudo rkt list | grep etcd | cut -f7 | cut -d'=' -f2)
        if [[ "$PROCESSION_TEST_ETCD_HOST" != "" ]]; then
            echo "ok."
            break
        fi
    done
    echo "etcd running in container at $PROCESSION_TEST_ETCD_HOST."
fi

sudo systemctl reset-failed

echo -n "Checking if procession-iamd running ... "

PROCESSION_SERVER_UNIT=$( systemctl | grep procession-iamd | grep running | sed 's/\s\+/ /g' | cut -d' ' -f1 )
if [[ "$PROCESSION_SERVER_UNIT" != "" ]]; then
    echo "yes."
    echo -n "Shutting down procession-iamd service $PROCESSION_SERVER_UNIT ... "
    sudo systemctl stop $PROCESSION_SERVER_UNIT
    sleep 1
    echo "ok."
else
    echo "no."
fi

echo -n "Starting locally-built Procession IAM server using systemd-run ... "
PROCESSION_SERVER_UNIT=`sudo systemd-run --slice=machine \
    --unit testing-procession-iamd \
    --setenv GSR_LOG_LEVEL=$GSR_LOG_LEVEL \
    --setenv PROCESSION_LOG_LEVEL=$PROCESSION_LOG_LEVEL \
    --setenv GSR_ETCD_ENDPOINTS=$GSR_ETCD_ENDPOINTS \
    --setenv PROCESSION_DSN=$PROCESSION_DSN \
    $ROOT_DIR/build/bin/procession-iamd 2>&1 | sed 's/\s\+//g' | cut -d':' -f2`
echo "ok."
echo "Procession IAM server running in $PROCESSION_SERVER_UNIT"
