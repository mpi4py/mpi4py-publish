#!/bin/bash
set -euo pipefail

mpich=("4.3" "4.1" "3.4")
openmpi=("5.0" "4.1")
impi=("2021.14.1" "2021.10.0")
msmpi=("10.1.1")

mpi="$1"
mpipackage="$mpi"
mpiversion="${mpi}[@]"
test "$mpi" = impi && mpipackage=impi_rt

CONDA=$(command -v micromamba || command -v mamba || command -v conda)
scriptdir=$(dirname "${BASH_SOURCE[0]}")
for version in "${!mpiversion}"; do
    echo "::group::$mpipackage=$version"
    "$CONDA" install -qy "$mpipackage=$version"
    "$CONDA" list
    "$scriptdir"/run-tests-mpi.sh
    echo "::endgroup::"
done
