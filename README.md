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
- `/admin/`: user and group management
