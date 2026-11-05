# kkr_transport

Small Django project for login and user authentication.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Folders

- `config/`: project settings and URL configuration.
- `accounts/`: login, logout, and protected user page.
- `templates/`: shared HTML layout.
- `static/css/`: CSS files.
- `.env`: local PostgreSQL and Django configuration.

## URLs

- `/accounts/login/`: login
- `/accounts/logout/`: logout
- `/accounts/`: protected page after login
- `/dashboard/super-admin/`: frontend super-admin dashboard

## Staff accounts

Only a superuser can access the frontend super-admin dashboard and create staff accounts:

1. Sign in as the superuser.
2. Select **Create staff account**.
3. Enter the staff member's name, phone number, and password. The phone number is the staff member's login ID.

After signing in, a staff user is sent to `/dashboard/`. Superusers are sent to the frontend super-admin dashboard. Staff users cannot create users, staff profiles, or other admin records.

Login sessions remain active for eight hours or until the user selects **Logout**. Logout is a POST action and clears the Django session. Protected dashboard responses are marked non-cacheable. Set `SESSION_COOKIE_AGE` in `.env` to change the session duration in seconds.
