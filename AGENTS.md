# AGENTS.md — Project Memory (read first, update last)

## SSH Access

```bash
ssh -o StrictHostKeyChecking=no -i /home/matrix/Desktop/brain/tennis_bot_vf/sports-trading/oraclessh.key ubuntu@161.118.182.103
```
Alias: `tennisbotdata.duckdns.org` → `161.118.182.103`

## Deploy Workflow

After pushing to GitHub (`saksh-2505/tennis_bot_vf`), deploy on Oracle VM:

```bash
ssh -i sports-trading/oraclessh.key ubuntu@161.118.182.103 "
cd ~/tennis_bot && git pull &&
cd console && npm install && npm run build && cd .. &&
rm -rf ~/console/.next && mkdir -p ~/console && cp -r console/.next ~/console/.next &&
docker compose build console_api && docker compose up -d console_api
"
```

For non-console changes (app/monitor only):
```bash
ssh -i sports-trading/oraclessh.key ubuntu@161.118.182.103 "
cd ~/tennis_bot && git pull &&
docker compose build app monitor && docker compose up -d
"
```

## Key Files

| File | Purpose |
|------|---------|
| `architecture.md` | Full system architecture reference |
| `console/lib/api.ts` | Frontend TypeScript interfaces (MUST match backend models) |
| `console_api/models.py` | Backend Pydantic response models |
| `console_api/routers/` | Backend endpoint implementations |
| `console/app/` | Next.js 14 frontend pages |
| `docker-compose.yml` | Docker service definitions |
| `config.py` | Pydantic settings from `.env` |
| `database.py` | SQLAlchemy engine + init |

## Critical Convention: Frontend ↔ Backend Alignment

The **#1 source of bugs** is the frontend TypeScript interfaces (`console/lib/api.ts`) diverging from the backend Python models (`console_api/models.py`). Every backend endpoint's return shape MUST match its frontend interface exactly. When adding/changing an API endpoint, update BOTH files.

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| `app` | — | Main platform (orchestrator + live collector) |
| `monitor` | — | Incident manager |
| `timescaledb` | 5432 | PostgreSQL 16 + TimescaleDB |
| `console_api` | 8000 | FastAPI backend + serves Next.js frontend |

## Console URL

`http://tennisbotdata.duckdns.org:8000`

## Project Rules

- After any build/deploy/modify, update `architecture.md`
- Module boundary rules: `incidents` imports `database` only; `collector` imports `models`, `shared`, `database`; etc. (see architecture.md §13)
- Never put secrets in source — use `.env`

## Git

- Repo: `saksh-2505/tennis_bot_vf` (GitHub)
- Branch: `main`
- Before commit: `git status`, `git diff`, `git log --oneline -5`
- Never force-push, never amend pushed commits, never skip hooks

## Last Session

- Full console frontend rebuild — 28 files changed to align frontend TypeScript interfaces with backend Python models
- Dashboard now shows real stats (1,456 matches, 4 live, 988 players, etc.)
- Fixed `/health` route ordering in `console_api/main.py` (moved before catch-all)

