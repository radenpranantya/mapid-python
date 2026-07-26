# n8n Workflow — Polygon QA Pipeline (Session 2)

**File:** [`mapid_polygon_pipeline.json`](mapid_polygon_pipeline.json)

## Architecture

```
Manual Trigger ──┐
                 ├── Set Variables → Execute Python Pipeline → IF success?
Schedule 08:00 ──┘                              ↙              ↘
                                         Cat Report       Set Failure
                                              ↓
                                       Send Email Report
                                              ↓
                                        Set Success
```

**Cat Report** runs `cat output/report.txt` so the email body uses `$json.stdout` (reliable on n8n 2.x).

## Start n8n (required env vars for n8n 2.x)

From repo root:

```bash
chmod +x scripts/start-n8n.sh
./scripts/start-n8n.sh
```

Or manually:

```bash
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"   # Node 20, not 26
export NODES_EXCLUDE='[]'
export N8N_RESTRICT_FILE_ACCESS_TO="$HOME/.n8n-files;/path/to/mapid-python/session-2"
n8n start
```

| Env var | Purpose |
|---------|---------|
| `NODES_EXCLUDE='[]'` | Enable **Execute Command** node |
| `N8N_RESTRICT_FILE_ACCESS_TO` | Allow reading `session-2/output/` |

## Import workflow

1. Open http://localhost:5678
2. **Workflows** → **Import from File** → `mapid_polygon_pipeline.json`
3. Update **Set Variables** and **Send Email Report** (see below)

## Set Variables

| Variable | Example |
|----------|---------|
| `pipeline_dir` | `/Users/raden/mapid-python/session-2` |
| `python_bin` | `/Users/raden/mapid-python/.venv/bin/python` |
| `report_email` | your recipient email |

## Gmail SMTP credential

| Field | Value |
|-------|--------|
| Host | `smtp.gmail.com` |
| Port | `587` |
| SSL/TLS | **OFF** |
| **Disable STARTTLS** | **OFF** (must be grey — STARTTLS enabled) |
| User | your@gmail.com |
| Password | Gmail **App Password** (not login password) |

**Send Email Report** node:

| Field | Value |
|-------|--------|
| From Email | same Gmail as SMTP user |
| To Email | `={{ $('Set Variables').item.json.report_email }}` |
| Subject | `=Polygon QA Report — {{ $now.format('yyyy-MM-dd') }}` |
| Text | `={{ $json.stdout }}` |

## Test workflow

```bash
# 1. Drop batch file in inbox
cp "$(ls -t session-2/data/generate_batch_polygons_*.json | head -1)" session-2/inbox/

# 2. In n8n: Test workflow on Manual Trigger
```

Expect email body = contents of `output/report.txt`.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `?` on Execute Command | Start n8n with `NODES_EXCLUDE='[]'` |
| `child_process` disallowed | Use Execute Command, not Code node |
| `Allowed paths: .n8n-files` | Set `N8N_RESTRICT_FILE_ACCESS_TO` |
| `530 STARTTLS` | Gmail: port 587, **Disable STARTTLS = OFF** |
| Email body `undefined` | Re-import workflow (uses Cat Report + `$json.stdout`) |
| Node 26 install fails | Use Node 20: `brew install node@20` |
