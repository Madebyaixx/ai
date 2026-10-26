#!/usr/bin/env bash
# Renders the reel: soundtrack -> frames (with motion blur) -> muxed vertical MP4.
set -euo pipefail
cd "$(dirname "$0")"
python3 audio.py
node render.mjs --samples "${SAMPLES:-4}" --workers "${WORKERS:-4}"
ffmpeg -y -loglevel error -i out/video.mp4 -i out/soundtrack.wav \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart out/claude-dashboards-explainer.mp4
ffmpeg -y -loglevel error -ss 9.9 -i out/claude-dashboards-explainer.mp4 -frames:v 1 out/cover.jpg
rm -f out/video.mp4
echo "done: out/claude-dashboards-explainer.mp4"
