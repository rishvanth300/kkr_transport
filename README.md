# kkr_transport

Small Django project for transport management.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Folders

- `config/`: project settings and URL configuration.
- `accounts/`, `fleet/`, `trips/`, `dashboard/`, `reports/`: application modules.
- `templates/`: project-wide HTML templates.
- `<module>/templates/<module>/`: HTML templates owned by one module.
- `static/css/`: CSS files.
- `media/`: uploaded images and other user files.
