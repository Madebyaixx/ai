#!/usr/bin/env bash
# Renders the full showreel: soundtrack -> frames (with motion blur) -> muxed MP4.
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
node render.mjs --samples "${SAMPLES:-6}" --workers "${WORKERS:-4}"
ffmpeg -y -loglevel error -i out/video.mp4 -i out/soundtrack.wav \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart out/claude-showreel-2026.mp4
ffmpeg -y -loglevel error -ss 14.9 -i out/claude-showreel-2026.mp4 -frames:v 1 out/poster.jpg
rm -f out/video.mp4
echo "done: out/claude-showreel-2026.mp4"
