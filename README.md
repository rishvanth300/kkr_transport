# KKR Transport

Django transport management system with Super Admin and Staff login.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Create the first Super Admin only if needed:

```powershell
python manage.py createsuperuser
```

## Main URLs

- `/accounts/login/` - Login
- `/dashboard/super-admin/` - Super Admin dashboard
- `/dashboard/` - Staff dashboard

Super Admins create and manage Staff accounts. Staff use their phone number and password to log in.
