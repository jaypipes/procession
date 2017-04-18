# Developing

## Dependencies

We use the excellent [govendor](https://github.com/kardianos/govendor) utility
for managing Golang package dependencies. To install, simply do: `go get -u
github.com/kardianos/govendor`.

### Install dependencies on newly-cloned Procession repository

If you are just starting out developing on a new `git clone`d Procession repository,
you will want to install all the Golang package dependencies required for
running Procession services and tests. To do so, issue the `govendor sync` command.

### Adding a new Golang package as a dependency

Note that there is a *single* `vendor/` directory in the Procession source
repository. We do not use nested `vendor/` repositories. All dependencies for
all Procession services are stored in the top-level `vendor/` directory.

To add a brand new Golang package to the list of dependent libraries, use the
`govendor fetch` command. For example, suppose I wanted to add the etcd client
package to Procession's list of dependent Golang libraries, I would do:

```
$ govendor fetch github.com/coreos/etcd/client
```

`govendor fetch` will grab the latest code from the specified library. You can
also pin to a particular release or git tag. See the `govendor` documentation
for details on how to do that.

### Caveats and best practices

**DO NOT** include vendored source code in pushed patches. Only the
`vendor/vendor.json` file should be included in the git commit, along with the
code that uses the new or updated Golang package. There is a .gitignore rule
that automatically excludes the `vendor/` folder, so you should by default
never add vendored source code to the git index.

## Protobuffer object model and gRPC

Procession uses [Google Protocol
Buffers](https://developers.google.com/protocol-buffers/) as its versioned
object system. Messages are sent between the Procession services using the
[gRPC](http://www.grpc.io/) framework, which uses Google Protocol Buffers as
its data exchange format.

The definition of objects and gRPC interfaces are located in the
[proto/defs/](proto/defs/) directory. All gRPC interfaces are contained in
files beginning with `service_`, for example the Identity and Access Management
gRPC interface is defined in the
[proto/defs/service\_iam.proto](proto/defs/service_iam.proto) file.

Protobuffer Golang code files are generated into the [proto/](proto) directory
by calling `make generated` from the root source directory.

If you add or change any `.proto` files, you will need to re-generate the
Protobuffer Golang code files. Once done, you can import all object definition and gRPC interface definitions in your Golang code by adding the following import:

```go
import (
    pb "github.com/jaypipes/procession/proto"
)
```
