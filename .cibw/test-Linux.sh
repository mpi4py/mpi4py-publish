#!/bin/bash
set -euo pipefail

sudo=$(command -v sudo || true)

(source /etc/os-release && echo "::group::$NAME $VERSION")

if grep -qE 'ID=(debian|ubuntu)' /etc/os-release; then
    packages=(
        python3-venv
        pypy3
        libmpich12
        libopenmpi3
    )
    export DEBIAN_FRONTEND=noninteractive
    $sudo apt update -y
    $sudo apt install -y ${packages[@]}
    multiarch=$(arch | sed s/^ppc/powerpc/)-linux-gnu
    $sudo ln -sr /usr/lib/$multiarch/libmpi{ch,}.so.12
fi

if grep -qE 'ID=fedora' /etc/os-release; then
    packages=(
        python3.6
        python3.7
        python3.8
        python3.9
        python3.10
        python3.11
        python3.12
        pypy3.9
        pypy3.10
        mpich
        openmpi
    )
    opts=--setopt=install_weak_deps=False
    $sudo dnf install -y $opts ${packages[@]}
    set +u
    source /etc/profile.d/modules.sh
    set -u
fi

echo "::endgroup::"

sdir=$(cd "$(dirname -- "$0")" && pwd -P)
$sdir/test-basic.sh
