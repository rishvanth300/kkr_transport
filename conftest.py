"""Pytest bootstrap — ensure Django settings before app imports."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_pkg.local")
