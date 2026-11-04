# TCMS — Project Structure (SRS reference)

Source of truth for what to build and in what order: `SRS.md` (v1.0, 2026-11-03).
This branch (`feature/project-structure`) creates the skeleton **only** — no
module logic, models, views, or business rules yet. Each module later gets its
own `feature/<module>` branch + PR — never push directly to `dev`.

## Branch process (per module)

```
dev  ────────────────────────────────  integration branch
  └─ feature/<module>  →  PR  →  dev   one branch per user story/module
```

1. `git checkout dev && git pull`
2. `git checkout -b feature/<module>` (e.g. `feature/module-1-accounts`)
3. Implement only that module's SRS requirements (FR-IDs in code comments).
4. `python manage.py check` + `pytest` + `ruff check .` must pass.
5. Open PR against `dev`; merge; delete feature branch.

## Layout

```
kkr_transport/
├── manage.py                  # DJANGO_SETTINGS_MODULE=config.settings_pkg.local
├── config/
│   ├── settings_pkg/
│   │   ├── base.py            # env vars, Postgres via dj-database-url, axes, WhiteNoise
│   │   ├── local.py           # DEBUG=True, lenient hosts
│   │   └── prod.py            # DEBUG=False, HTTPS+HSTS, pinned hosts (Appendix C)
│   ├── urls.py                # root routing: /accounts /fleet /trips /dashboard /reports
│   ├── wsgi.py / asgi.py
│   └── __init__.py
├── accounts/                  # M-01 auth, M-02 roles, M-08 audit — Module 1
│   ├── models.py              # UserProfile(role), AuditLog — TBD
│   ├── views.py / urls.py / admin.py / tests.py
│   ├── management/commands/   # e.g. seed/reset commands
│   ├── templates/accounts/  static/accounts/
│   └── utils/ / filters/
├── fleet/                     # M-03 vehicles, M-04 drivers — Module 2
│   ├── models.py              # Vehicle, Driver, DriverVehicleAssignment — TBD
│   └── (same sub-structure as accounts)
├── trips/                     # M-05 core — Module 3
│   ├── models.py              # Trip (15 fields + net_margin + soft delete) — TBD
│   └── (same sub-structure)
├── dashboard/                 # M-06 — Module 4 (no tables, aggregations only)
├── reports/                   # M-07 — Module 5 (no tables, CSV/PDF on request)
├── templates/                 # global chrome: base.html, _includes/, registration/
├── static/                    # css/ js/ img/ vendor/ (Chart.js vendored, no CDN)
├── tests/                     # integration / acceptance tests
├── docs/                      # STRUCTURE.md, restore.md, README-APPENDIX
├── scripts/
└── requirements.txt           # pinned (NFR-SEC-010)
```

## Settings map (SRS §5.6 NFR-MAIN-001)

| Setting | `base.py` | `local.py` | `prod.py` |
|---|---|---|---|
| DEBUG | env (default False) | True | False |
| ALLOWED_HOSTS | env | localhost + * | pinned (env) |
| DATABASE_URL | Neon/Supabase SSL or SQLite fallback | local Postgres | Neon/Supabase SSL |
| Secure cookies / SSL redirect | env | off | on |
| HSTS | env | 0 | ≥180 days |
| Axes lockout | 5 fails / 15 min (FR-AUTH-002) | same | same |

## Database

PostgreSQL only in production (§2.5). Local dev uses the same engine via
`DATABASE_URL=postgres://.../kkr_transport`. If `DATABASE_URL` is unset the app
falls back to SQLite **only** so `manage.py check` passes offline — do not
deploy that config (ephemeral disk = data loss).

## Next steps (user stories, one at a time)

1. **Module 1 — accounts:** `UserProfile` + roles, login/logout, axes lockout,
   `AuditLog`, admin. Tests: driver A cannot see driver B (AC-02).
2. **Module 2 — fleet:** Vehicle + Driver masters, assignments, soft-deactivate.
3. **Module 3 — trips:** Trip model (15 fields), RBAC querysets, soft delete.
4. **Module 4 — dashboard:** per-vehicle KPIs + Chart.js (P95 ≤ 2s, AC-05).
5. **Module 5 — reports:** monthly statement CSV/PDF, export audit (AC-03).
