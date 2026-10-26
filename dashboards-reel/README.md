# Claude Dashboards: 28-second reel explainer

A vertical (1080×1920, 60 fps) explainer for Claude Dashboards, the beta feature
Anthropic launched on 8 October 2026. Built for Reels, Shorts and TikTok: burned-in
captions for muted viewing, and key content kept clear of the platform UI at the top
and bottom of the frame.

**Watch:** [`out/claude-dashboards-explainer.mp4`](out/claude-dashboards-explainer.mp4)

## Script

| Time | Beat | On screen |
|------|------|-----------|
| 0:00 | Hook | "Ask a question. Get a live dashboard." |
| 0:03 | Step 1 | A prompt is typed: *Build a live dashboard of our Q4 pipeline by region from Salesforce.* |
| 0:07 | Step 2 | The prompt box morphs into the dashboard: KPIs count up, bars grow, the trend line draws in |
| 0:11.5 | Step 3 | Data sources connect: BigQuery, Snowflake, Databricks, ClickHouse, Amazon Redshift, Salesforce, plus your other connectors |
| 0:15 | Step 4 | The clock runs forward an hour, new data arrives, the "updated" timestamp refreshes |
| 0:18.5 | Step 5 | A tap on a number opens the SQL behind it, and Claude explains the query |
| 0:22 | Step 6 | Private by default, then shared: each viewer sees only the regions they already have access to |
| 0:25.5 | End card | Beta on Pro, Max, Team & Enterprise. Enterprise admins enable it in Organization settings → Artifacts |

All numbers in the dashboard are sample data. Feature details reflect launch coverage
of the beta and may change.

## Files

- `index.html` – the animation. Open it in a browser for a real-time preview.
- `render.mjs` – frame-exact renderer (headless Chromium + ffmpeg).
- `audio.py` – original soundtrack and UI sound design (numpy only).
- `build.sh` – full build → `out/claude-dashboards-explainer.mp4`.
