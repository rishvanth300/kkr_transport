"""ASGI config for TCMS — production uses gunicorn (WSGI) per SRS Appendix A."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_pkg.local")

application = get_asgi_application()
