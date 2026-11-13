# KKR Transport

Django-based transport management application for KKR Transport. It provides role-based access (Super Admin and Staff), fleet master data management (vehicles/drivers/companies), trip sheet operations with server-calculated financials, driver bata/advance settlement tracking, and dashboard/financial summaries.

This README describes the application as implemented in the current source code.

## 1. Project overview

- **Framework**: Django 5.2 (server-rendered templates)
- **Database**: PostgreSQL (`django.db.backends.postgresql`)
- **Authentication**: Django auth with phone-number login identifier (stored in `auth_user.username`)
- **Roles**:
  - **Super Admin**: Django superuser (`is_superuser=True`)
  - **Staff**: non-superuser user with an active `accounts.Staff` profile and active user account
- **Primary domains**:
  - Accounts/login and staff profiles
  - Dashboard and staff administration
  - Fleet (companies, vehicles, drivers)
  - Trips (trip sheets, diesel entries, driver advances, bata allocations)
  - Reports app scaffold (no active routes/views implemented)

## 2. Technology stack

- Python + Django (`Django==5.2.18`)
- PostgreSQL driver: `psycopg[binary]>=3.1,<4`
- Environment loading: `python-dotenv>=1.0,<2`
- Frontend: Django templates (`templates/` and app template folders), static assets (`static/`)
- Time zone: `Asia/Kolkata` (`USE_TZ=True`)

## 3. Complete folder structure (top-level)

```text
.
├─ .env / .env.example          # Runtime environment configuration
├─ manage.py                   # Django management entrypoint
├─ requirements.txt            # Python dependencies
├─ README.md                   # Project documentation
├─ LICENSE
├─ config/                     # Django project package (settings, root URLs, WSGI/ASGI)
├─ accounts/                   # Staff profile, login/logout/home routing
├─ dashboard/                  # Role decorators, dashboards, staff management, metrics services
├─ fleet/                      # Company/Vehicle/Driver models, forms, views, admin
├─ trips/                      # Trip sheets, diesel, advances/allocations, finance services
├─ reports/                    # Placeholder app (no URL routes)
├─ templates/                  # Shared/base templates
├─ static/                     # Static assets
└─ media/                      # Uploaded/media files (runtime)
```

## 4. Folder and module responsibilities

### `config/`
- `settings.py`: Environment-driven settings (secret key, debug, hosts, DB, installed apps, middleware, templates, static/media, session/auth defaults, trip finance default `DEFAULT_DRIVER_BATA_PERCENTAGE`).
- `urls.py`: Root routes (`/`, `/healthz`, `/accounts/`, `/dashboard/`, `/fleet/`, `/trips/`, `/admin/`).
- `asgi.py`, `wsgi.py`: ASGI/WSGI application entrypoints.
- `__init__.py`: Package marker.

### `accounts/`
- `models.py`: `Staff` (OneToOne to `AUTH_USER_MODEL`, display name, unique phone number, active flag).
- `views.py`: Phone-number login view (`AccountLoginView`), logout, role-based home redirect.
- `urls.py`: `login/`, `logout/`, and app home.
- `admin.py`: Staff admin and inline on Django `User` admin.
- `apps.py`: App config.
- `migrations/`: Staff schema history.

### `dashboard/`
- `views.py`: Authorization decorators (`superadmin_required`, `staff_required`, `dashboard_access_required`), staff CRUD/password/reset/toggle actions, dashboards (super admin, staff home, trucks, drivers, financial overview, audit logs).
- `services.py`: Date/filter resolution, trip/operational/financial aggregations, chart and vehicle distribution data, vehicle financial summary helpers.
- `forms.py`: Super Admin staff creation/edit and password reset forms (atomic user/profile updates).
- `urls.py`: Dashboard and staff-management routes.
- `apps.py`: App config.

### `fleet/`
- `models.py`: `Company`, `Vehicle`, `Driver` (optional assignment to vehicle).
- `forms.py`: Vehicle registration and driver create/edit forms with normalization/validation (registration uniqueness, mobile/licence validation, etc.).
- `views.py`: Vehicle add/detail/financial views and driver list/add/detail/edit views.
- `urls.py`: Fleet routes.
- `admin.py`: Admin registrations/search/list configuration.
- `migrations/`: Fleet schema history (vehicle, driver, company).

### `trips/`
- `models.py`: `TripSheet`, `DieselEntry`, `DriverAdvance`, `DriverBataAllocation`; financial fields, validation, helper properties/aliases, and calculation trigger hook.
- `services.py`: Canonical trip financial calculation, diesel-entry synchronization/aggregation support, atomic trip save, driver finance summaries/outstanding calculations, advance+allocation creation, scoped trip queryset.
- `forms.py`: Truck selection, trip sheet form (truck-first selected vehicle handling, defaults/normalization/validation), driver advance form with optional same-driver trip allocation.
- `views.py`: Trip dashboard/list/filtering, truck-first create flow, detail/edit/delete/print, driver finance list/detail, advance creation.
- `urls.py`: Trip routes.
- `admin.py`: Trip/admin inlines and save hooks to keep derived financials consistent.
- `migrations/`: Trips schema history (including company FK → `company_name` transition and bata percentage fields).

### `reports/`
- `apps.py`, `urls.py`, `views.py`, `__init__.py`: Scaffold only; `urlpatterns` is empty and no report views are implemented.

### `templates/` and app templates
- `templates/base.html`, `templates/dashboard/layout.html`: Shared base/layout templates.
- App template folders contain page templates for accounts, dashboard, fleet, trips, and reports scaffold UI.

## 5. Python file inventory (responsibilities)

| File | Responsibility |
|---|---|
| `manage.py` | CLI entrypoint; sets `DJANGO_SETTINGS_MODULE=config.settings`. |
| `config/settings.py` | Project configuration, DB/auth/static/media/session, finance default setting. |
| `config/urls.py` | Root URL dispatch and health endpoint. |
| `config/asgi.py` / `config/wsgi.py` | Server interface entrypoints. |
| `accounts/models.py` | Staff profile data model. |
| `accounts/views.py` | Login, logout, role/home routing. |
| `accounts/urls.py` | Accounts URL patterns. |
| `accounts/admin.py` | Admin integration for staff/users. |
| `dashboard/forms.py` | Staff account create/edit/password-reset forms. |
| `dashboard/views.py` | Access control, staff admin actions, dashboard pages. |
| `dashboard/services.py` | Aggregations, date/filter logic, charts/distribution summaries. |
| `dashboard/urls.py` | Dashboard/staff-management URL patterns. |
| `fleet/models.py` | Company, vehicle, driver schema. |
| `fleet/forms.py` | Fleet input validation and normalization. |
| `fleet/views.py` | Fleet CRUD/detail/financial pages. |
| `fleet/urls.py` | Fleet URL patterns. |
| `fleet/admin.py` | Fleet admin configuration. |
| `trips/models.py` | Trip and driver-finance transaction schema, validation, derived-value helpers. |
| `trips/services.py` | Trip financial calculations, persistence helpers, driver finance computations. |
| `trips/forms.py` | Trip and advance form validation/workflow support. |
| `trips/views.py` | Trip workflow/pages, filters, settlements context, driver finance pages. |
| `trips/urls.py` | Trips URL patterns. |
| `trips/admin.py` | Trip admin behavior and recalculation hooks. |
| `reports/views.py` / `reports/urls.py` | Placeholder (no implemented routes). |

> Note: `__init__.py`, `apps.py`, and migration files are standard/supporting modules; migrations define schema evolution and must not be edited retroactively.

## 6. Application execution flow

1. **Request entry**: Browser/client hits `config.urls` routes.
2. **Authentication** (`accounts`):
   - `/accounts/login/` authenticates via Django auth (phone number used as username).
   - On success, users are redirected by role (super admin dashboard, active staff dashboard, or fallback).
   - `/accounts/logout/` logs out via POST and redirects to login.
3. **Authorization** (`dashboard.views` decorators):
   - Super-admin-only actions use `superadmin_required`.
   - Operational dashboards/fleet/trips pages generally use `dashboard_access_required` (superuser or active staff profile required).
4. **Dashboard/operations**:
   - Dashboard pages render metrics and records via `dashboard.services` and app querysets.
   - Super Admin manages staff accounts and can toggle/edit/reset passwords.
5. **Fleet management** (`fleet`):
   - Vehicles and drivers are created/edited/viewed; drivers may be assigned to vehicles.
   - Vehicle financial view uses trip aggregates for a selected vehicle.
6. **Trip workflow** (`trips`, truck-first):
   - User selects an existing vehicle (`/trips/add/` flow), selection is validated/stored, then trip form is submitted.
   - `trips.services.calculate_trip_financials` computes derived values server-side; `save_trip_sheet` validates and saves atomically and syncs diesel summary/entries behavior.
   - Trip list/dashboard/filter views aggregate and display trip financials.
   - Driver advances and bata allocations are recorded as separate financial transactions; settlement context is shown on trip/detail/print and driver finance pages.
7. **Admin** (`/admin/`): Django admin for supported models with trip recalculation hooks.

## 7. Database table relationships and dependencies

### Core relationships
- `auth_user` (Django built-in)
  - `accounts_staff.user` → **OneToOne** to `auth_user` (`on_delete=CASCADE`)
- `fleet_vehicle`
  - `fleet_driver.assigned_vehicle` → **FK (nullable)** to `fleet_vehicle` (`on_delete=SET_NULL`)
- `trips_tripsheet`
  - `driver` → **FK** to `fleet_driver` (`PROTECT`)
  - `vehicle` → **FK** to `fleet_vehicle` (`PROTECT`)
  - `created_by` → **FK** to `auth_user` (`PROTECT`)
  - `company_name` is stored as text on `TripSheet` (current schema)
- `trips_dieselentry`
  - `trip_sheet` → **FK** to `trips_tripsheet` (`CASCADE`)
- `trips_driveradvance`
  - `driver` → **FK** to `fleet_driver` (`PROTECT`)
  - `recorded_by` → **FK** to `auth_user` (`PROTECT`)
- `trips_driverbataallocation`
  - `advance` → **FK** to `trips_driveradvance` (`PROTECT`)
  - `trip_sheet` → **FK** to `trips_tripsheet` (`PROTECT`)
  - `allocated_by` → **FK** to `auth_user` (`PROTECT`)
- `fleet_company` exists as a master table; in the current trip schema/company workflow, trip company is represented by `TripSheet.company_name` (historical migration moved from company FK to name field).

### Foreign-key dependency hierarchy (creation order)
1. Django/auth core tables (including `auth_user`)
2. `fleet_vehicle`, `fleet_company` (independent)
3. `fleet_driver` (optional dependency on `fleet_vehicle`)
4. `accounts_staff` (depends on `auth_user`)
5. `trips_tripsheet` (depends on `fleet_driver`, `fleet_vehicle`, `auth_user`) and `trips_driveradvance` (depends on `fleet_driver`, `auth_user`)
6. `trips_dieselentry` (depends on `trips_tripsheet`) and `trips_driverbataallocation` (depends on `trips_driveradvance`, `trips_tripsheet`, `auth_user`)

> Do not manually create/drop production tables to "fix" dependencies; rely on Django migrations in order.

## 8. Financial calculation semantics (as implemented)

- **Trip distance**: `closing_km - starting_km` (non-negative)
- **Diesel cost**: `diesel_quantity * diesel_price_per_litre`
- **Mileage**: `distance_km / diesel_quantity` when quantity > 0, else `None`
- **Driver bata (trip expense)**: `total_revenue * bata_percentage / 100` (stored per trip)
- **Trip total cost (expenses)**: diesel + loading + unloading + toll + driver bata + load commission + maintenance + other expenses
- **Trip profit**: `total_revenue - total_cost`
- **Driver advances and bata allocations** are separate financial transactions tracked outside trip expense/profit totals (settlements reduce payable/outstanding balances as implemented).

## 9. How Django communicates with PostgreSQL

- Database connection is configured in `config/settings.py` under `DATABASES["default"]` using environment variables:
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Django ORM models/migrations define schema and queries.
- At runtime, Django uses `psycopg` to execute SQL against PostgreSQL for ORM operations, aggregations, and transactions (e.g. atomic trip save/advance allocation flows).
- Schema changes are applied through Django migrations (`python manage.py migrate`), not manual table edits.

## 10. Setup and local run

### Prerequisites
- Python (compatible with Django 5.2)
- PostgreSQL server/database accessible with configured credentials
- Virtual environment recommended

### Install
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Configure environment
Create/update `.env` (see `.env.example`) with at least:
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Optional: `SESSION_COOKIE_AGE`, `DEFAULT_DRIVER_BATA_PERCENTAGE`

### Run
```powershell
python manage.py migrate
python manage.py runserver
```

Create an initial Super Admin if needed:
```powershell
python manage.py createsuperuser
```

## 11. Main URLs

- `/` → redirects to login
- `/healthz` → health JSON response
- `/accounts/login/` → login
- `/accounts/logout/` → logout (POST)
- `/dashboard/` → staff dashboard (role-routed behavior)
- `/dashboard/super-admin/` → super admin dashboard
- `/dashboard/financial/` → financial overview
- `/fleet/...` → vehicle/driver management routes
- `/trips/...` → trip sheet workflow, lists, details, driver finance, advances
- `/admin/` → Django admin

> `/reports/` has no active routes in current implementation.

## 12. Running migrations safely (existing application)

- **Do not delete or modify existing migration files**.
- **Do not rename existing database tables or model fields** unless explicitly planned as a separate, reviewed schema-change effort.
- Apply migrations in order with:
  ```powershell
  python manage.py migrate
  ```
- Before applying migrations in production/staging:
  - back up the database
  - verify environment points to the intended database
  - review pending migrations: `python manage.py showmigrations`
  - deploy during a controlled window if schema/data migrations are involved
- If a migration/data issue is suspected, stop and investigate; do not hand-edit migration history to "force" consistency.

## 13. Running tests and checks

```powershell
python manage.py check
python manage.py test
```

Notes:
- Test database creation requires appropriate PostgreSQL permissions for the configured user.
- For performance-sensitive changes, compare query counts on key flows (trip lists/detail, driver finance, dashboards) before/after in a representative environment.

## 14. Production deployment considerations

- Set `DEBUG=False`, strong `SECRET_KEY`, and explicit `ALLOWED_HOSTS`.
- Use secure PostgreSQL credentials and network controls; restrict DB access.
- Run `collectstatic` and serve static files appropriately for your deployment stack.
- Use a production-grade WSGI/ASGI server (not `runserver`).
- Configure HTTPS, secure cookies, CSRF/trusted origins, logging, backups, and monitoring per your infrastructure standards.
- Preserve existing business logic, API/URL behavior, and schema contracts unless changes are explicitly approved and tested.
- Validate migrations and perform backups before deploys; avoid ad-hoc production data edits.

## 15. Known implementation notes (current code)

- `reports` app is currently a placeholder (no URLs exposed).
- Trip financial derivations are centralized in `trips.services` and also enforced in admin save hooks to keep stored derived values consistent.
- Driver finance views compute totals and settlement context from stored trip/advance/allocation records; advances/allocations are treated as separate from trip expenses and company profit.
