#!/usr/bin/env bash
# Fetch the smina docking binary.
#
# Not vendored into the repo: it is a ~10 MB platform-specific binary, and
# committing it would bloat clones for everyone who never runs docking.
#
# smina rather than AutoDock Vina's own build for two practical reasons. The
# vina Python package needs Boost headers to compile, which are not present in
# a plain uv environment. And smina links OpenBabel internally, so it reads a
# PDB receptor directly — which matters here because MAO-B carries an FAD
# cofactor that Meeko has no template for, and stripping FAD to satisfy the
# preparation step would open a binding cavity that does not exist in reality.
set -euo pipefail

DEST="$(cd "$(dirname "$0")/.." && pwd)/backend/bin"
mkdir -p "$DEST"

echo "Fetching smina -> $DEST/smina"
curl -sL --fail -m 300 -o "$DEST/smina" \
  "https://sourceforge.net/projects/smina/files/smina.static/download"
chmod +x "$DEST/smina"

"$DEST/smina" --version
