#!/bin/bash
set -euo pipefail

wheelhouse=${1:-wheelhouse}

tempdir=$(mktemp -d)
trap "rm -rf $tempdir" EXIT
for wheel in $wheelhouse/*.whl; do
    wheeldir=$tempdir/$(basename $wheel).dir
    unzip -qq $wheel -d $wheeldir
    distinfo=$(basename $wheeldir/mpi4py*.dist-info)
    mkdir -p $wheeldir/${distinfo%%-*}.libs
    mkdir -p $wheeldir/mpi4py/.dylibs
done

libs=""
rpath=""
runpath=""
needed=""

if [ $(uname) == Linux ]; then
    pdir=$tempdir/mpi4py*linux*.dir
    ldir=$tempdir/mpi4py*linux*.dir/mpi4py*.libs
    mods=$(ls $pdir/mpi4py/MPI.*.so)
    libs=$(find $ldir -type f -exec basename {} \; | sort | uniq)
    rpath=$(patchelf --print-rpath --force-rpath $mods | sort | uniq)
    runpath=$(patchelf --print-rpath $mods | sort | uniq)
    needed=$(patchelf --print-needed $mods | sort | uniq)
fi

if [ $(uname) == Darwin ]; then
    pdir=$tempdir/mpi4py*macos*.dir
    ldir=$tempdir/mpi4py*macos*.dir/mpi4py/.dylibs
    mods=$(ls $pdir/mpi4py/MPI.*.so)
    libs=$(find $ldir -type f -exec basename {} \; | sort | uniq)
    needed=$(otool -L $mods | awk '/ /{print $1}'| sort | uniq)
fi

if [[ $(uname) =~ NT ]]; then
    pdir=$tempdir/mpi4py*win*.dir
    mods=$(ls $pdir/mpi4py/MPI.*.pyd)
    for m in $mods; do cp $m $m.dll; done
    mods=$(ls $pdir/mpi4py/MPI.*.dll)
    lddout=$(mktemp -d)/ldd.out
    for m in $mods; do
        ldd $m | grep -v $(basename $m) >> $lddout;
    done
    cpy='^\spython.*\.dll\s=>\s'
    ppy='^\slibpypy.*\.dll\s=>\s'
    mpi='^\s\(i\|ms\)mpi\.dll\s=>\s'
    crt='^\sapi-ms-win-crt-.*\.dll\s=>\s'
    sys='/[a-z]/Windows/System32/'
    libs=$( \
       cat $lddout | \
       (grep -v -i -e $sys -e $crt -e $cpy -e $ppy -e $mpi || true) | \
       awk '/=>/{print $1}' | sort -f | uniq)
    needed=$(\
       cat $lddout | \
       (grep -v -i -e $sys -e $crt -e $cpy -e $ppy || true) | \
       awk '/=>/{print $1}' | sort -f | uniq)
fi

echo libs:    $libs
echo rpath:   $rpath
echo runpath: $runpath
echo needed:  $needed

test -z "$libs"
test -z "$rpath"
test -z "$runpath"
