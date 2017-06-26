PROTO_DIR := $(shell pwd)/proto
PROTO_DEFS_DIR := $(shell pwd)/proto/defs

build: build-iam build-p7n

build-iam: generated
	@echo -n "Building procession-iamd ... "
	@go build -o build/bin/procession-iamd iam/main.go && echo "ok."

build-p7n: generated
	@echo -n "Building p7n client tool ... "
	@go build -o build/bin/p7n p7n/main.go && echo "ok."

# Ensures vendor code is installed in /vendor according to the vendor.json
# manifest
vendored-ensure:
	@echo -n "Ensuring vendored code available locally ... "
	@./scripts/vendored.bash --ensure && echo "ok."

# Pulls latest versions of vendored code and updates vendor/vendor.json
# manifest
vendored-update:
	@echo -n "Updating vendored code ... "
	@./scripts/vendored.bash && echo "ok."

# Generates protobuffer code
generated: vendored-ensure
	@echo -n "Generating protobuffer code from proto definitions ... "
	@protoc -I $(PROTO_DEFS_DIR) \
	       $(PROTO_DEFS_DIR)/*.proto \
	       --go_out=plugins=grpc:$(PROTO_DIR) && echo "ok."

test: test-unit test-e2e

test-unit: build
	@echo "Running unit tests ... "
	@go test ./...

test-e2e: build
	@echo "Running end-to-end tests ... "
	@./e2e/run_tests.bash
