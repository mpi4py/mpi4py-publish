#!/bin/bash
set -euo pipefail

images=(
    debian:10
    debian:11
    debian:12
    fedora:37
    fedora:38
    fedora:39
    ubuntu:20.04
    ubuntu:22.04
    ubuntu:23.10
)
arches=(
    x86_64
    aarch64
    ppc64le
)
sdir=$(cd "$(dirname -- "$0")" && pwd -P)

for image in ${images[@]}; do
    for arch in ${arches[@]}; do
        test $image-$arch == debian:10-ppc64le && continue
        ls dist | grep -q $arch || continue
        echo Running on $image $arch
        docker run \
          --rm \
          -v $(pwd):$(pwd):z \
          -w $(pwd) \
          --arch $arch \
          $image \
          bash $sdir/test-Linux.sh
    done
done
