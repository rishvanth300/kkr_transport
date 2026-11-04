#!/usr/bin/env bash
# TCMS — local pre-push checks (SRS NFR-MAIN-003).
set -euo pipefail
python manage.py check --settings=config.settings_pkg.local
python manage.py check --deploy --settings=config.settings_pkg.prod || true
ruff check .
python -m pytest -q
