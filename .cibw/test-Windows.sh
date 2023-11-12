#!/bin/bash
set -euo pipefail

sdir=$(cd "$(dirname -- "$0")" && pwd -P)
$sdir/test-basic.sh
