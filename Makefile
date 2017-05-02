BUILD_DIR := $(shell pwd)/build
PROTO_DIR := $(shell pwd)/proto
PROTO_DEFS_DIR := $(shell pwd)/proto/defs

# Generates protobuffer code
generated:
	@echo "Generating protobuffer code from proto definitions..."
	protoc -I $(PROTO_DEFS_DIR) \
	       $(PROTO_DEFS_DIR)/*.proto \
	       --go_out=plugins=grpc:$(PROTO_DIR)

SUBDIRS = iam

.PHONY: default clean subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	@$(MAKE) --no-print-directory -C $@ build

clean: bin-clean

bin-clean:
	rm -rf $(BUILD_DIR)/go
	rm -rf $(BUILD_DIR)/bin
