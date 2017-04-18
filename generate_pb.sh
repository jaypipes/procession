#!/bin/bash

ROOT_DIR=`pwd`
PROTO_DEFS_DIR=$ROOT_DIR/proto/defs

protoc -I $PROTO_DEFS_DIR \
       $PROTO_DEFS_DIR/*.proto \
       --go_out=plugins=grpc:proto
