# kkr_transport — Transport Company Management System (TCMS)

Django 5 + PostgreSQL trip & vehicle management app. Built from `SRS.md` v1.0;
see `docs/STRUCTURE.md` for the module map and branch process.

## Quick start (local)

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements-dev.txt
copy .env.example .env        # edit DATABASE_URL for local Postgres
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Login: http://localhost:8000/accounts/login/
- Health: http://localhost:8000/healthz
- First module (accounts) will add the real login (see `docs/STRUCTURE.md`).

## PostgreSQL

```bash
# Neon/Supabase: paste the SSL URL into DATABASE_URL (see .env.example)
createdb kkr_transport
# DATABASE_URL=postgres://postgres:postgres@localhost:5432/kkr_transport
```

SQLite fallback only when `DATABASE_URL` is unset — never deploy it.

## Checks

```bash
python manage.py check
python manage.py check --deploy --settings=config.settings_pkg.prod
python -m pytest -q
ruff check .
```

## Branching

One branch per module: `feature/<module>` → PR → `dev`. Never push directly
to `dev`. See `docs/STRUCTURE.md`.
