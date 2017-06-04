PROTO_DIR := $(shell pwd)/proto
PROTO_DEFS_DIR := $(shell pwd)/proto/defs

# Generates protobuffer code
generated:
	@echo "Generating protobuffer code from proto definitions..."
	protoc -I $(PROTO_DEFS_DIR) \
	       $(PROTO_DEFS_DIR)/*.proto \
	       --go_out=plugins=grpc:$(PROTO_DIR)

build-iam: generated
	@echo "Building procession-iamd ..."
	go build -o build/bin/procession-iamd iam/main.go

build-p7n: generated
	@echo "Building p7n client tool ..."
	go build -o build/bin/p7n p7n/main.go

e2e: build-iam build-p7n
	@echo "Running end-to-end tests ..."
	./e2e/run_tests.bash

build: build-iam build-p7n

test: e2e
