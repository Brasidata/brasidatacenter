#!/usr/bin/env bash
clear

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building HTML documentation from RDF..."
python3 "$SCRIPT_DIR/build.py"
echo "Done!"
