#!/bin/bash
# usage: video/cut.sh [out-dir]   -- needs ffmpeg and node; writes issue-desk-demo.mp4 and readme.gif into the out dir
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 video/cut.py "${1:-video/out}"
