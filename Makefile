PROTO_DIR := $(shell pwd)/proto
PROTO_DEFS_DIR := $(shell pwd)/proto/defs

# Generates protobuffer code
generated:
	@echo "Generating protobuffer code from proto definitions..."
	protoc -I $(PROTO_DEFS_DIR) \
	       $(PROTO_DEFS_DIR)/*.proto \
	       --go_out=plugins=grpc:$(PROTO_DIR)
