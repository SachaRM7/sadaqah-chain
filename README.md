# SadaqahChain

Self-hosted Telegram bot + FastAPI service for Zakat calculation, charity whitelisting, donation tracking, a public append-only ledger, polls, and weekly disbursement reporting.

## What is included

- Telegram bot entry point in `sadaqahchain.py`
- REST API in `api.py`
- SQLite schema and helpers in `db.py` + `schema.sql`
- Zakat calculation engine in `zakat_calculator.py`
- Public hash-chained ledger in `ledger.py`
- Charity whitelist management in `charities.py`
- Community polls in `polls.py`
- Weekly reports in `reports.py`
- APScheduler jobs in `cron_jobs.py`
- Combined launcher in `main.py`
- Basic tests in `tests/`

## Setup

```bash
cd /root/.hermes/agents/coder/code/20260423
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:

- `API_KEY`
- `BOT_TOKEN` if you want Telegram enabled
- `ADMIN_USER_IDS`
- `CHAT_ID` / `POLL_CHANNEL_ID` if you want channel automation

## Run the REST API + scheduler

```bash
python main.py
```

If `BOT_TOKEN` is empty, only FastAPI + scheduler run.

## Development commands

Run tests:

```bash
pytest tests -q
```

Run just the API:

```bash
uvicorn api:app --reload
```

## Notes

- The ledger uses a SHA256 hash chain (`previous_signature + current payload`) for tamper detection.
- The calculator is an engineering aid, not a fatwa.
- The database defaults to SQLite and performs nightly backups via APScheduler.
