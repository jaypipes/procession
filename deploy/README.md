# Deploying Procession

Procession uses a microservice application architecture. This means that deployment
of Procession is complex and requires the use of a number of supporting applications
like [rkt](https://github.com/coreos/rkt) and
[ACi](https://github.com/appc/spec/blob/master/spec/aci.md) for container image
execution and defintion, along with [Kubernetes](https://kubernetes.io/) for
handling the orchestration and VIP management for the services.

# Container image definitions

All services that comprise the Procession application, including infrastructure
services like etcd, MySQL, Prometheus, and memcached, are deployed in
containers. The containers are defined as
[ACI](https://github.com/appc/spec/blob/master/spec/aci.md) images in the
`deploy/` directory. Each service or infrastructure component has a separate
directory within the `deploy/aci/` directory that contains the ACI definition
for that service or infrastructure component. For example, the Procession API
service has its ACI image definition in the `deploy/aci/api/` directory.

The ACI image definition is simply a directory structure containing a file
called `manifest` and a subdirectory called `rootfs` that contains the things
that go in the image itself.

Image definitions are a critical piece of the Procession application and should be
treated in the same way as source code, because they are, in fact, source code.
They are configuration and infrastructure as code.

# How container images for services are built

Container images for services are built by a small Bash script called
`deploy/build-oci.bash` that looks for the ACI definition of a service and
constructs the ACI image from that definition. You can build a particular
service image manually by simply executing the script with the name of the
service or infrastructure component. For example, to build the ACI image for
the Procession API service, do the following:

```bash
$ ./deploy/container-build.bash procession-api
```

The `deploy/container-build.bash` script does a number of things to create the
ACI image, depending on whether the service is a Procession service or an
infrastructure component.

## Procession services

1.  The service binary is built from Go sources into the `build/` directory
2.  The rootfs subdirectory from the ACI directory for the service is read to
    determine whether the binary has already been injected into the `bin/`
    directory on the image's filesystem
3a. If the binary has **not** been written to the rootfs, the binary is copied
    from the `build/` directory to the `bin/` directory in the image rootfs
    filesystem
3b. If the binary has already been written to the rootfs, then binary diff is
    done against that binary and the one just placed in the `build/` directory,
    and if different, the binary in `build/` is copied into the image rootfs
    `bin/` directory
4.  
