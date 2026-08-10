#!/usr/bin/env bash
set -euo pipefail

# Real solver. Pulls torch, so this is the heavy path — the earlier sandbox
# here couldn't reach download.pytorch.org, but a GitHub-hosted runner has
# normal internet access,this is the first time it actually gets tested
# end to end rather than just read from source.
pip install --quiet vibecheck-nn
