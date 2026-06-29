# Reddit API — Build Me Up 🏗️

This is where the code goes. **All documentation is in `../reddit-api-docs/`.**

## How to Start

1. Read `../reddit-api-docs/prompt.md` — it tells OpenCode/AI exactly what to build
2. Read ALL docs in `../reddit-api-docs/` in the order specified in prompt.md
3. Then build everything here

## Quick Reference

| What | Where |
|------|-------|
| Docs & design | `../reddit-api-docs/` |
| Project code | `.` (this dir) |
| Vendor code | `vendor/` (clone repos here) |
| Runtime data | `data/` (gitignored) |

## After Building

```bash
# Verify it works
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/admin/health
```
