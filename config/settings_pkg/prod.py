"""Production settings — Render + Neon/Supabase Postgres (SRS Appendix B/C).

Enforces SRS FR-ADM-003 / Appendix C go-live checklist: DEBUG off, pinned
hosts, secure cookies, HTTPS + HSTS. Secrets via env vars only (NFR-SEC-001).
"""
import os

from .base import *  # noqa: F401,F403, F405
from .base import ALLOWED_HOSTS  # noqa: F401

DEBUG = False

# Pinned by deploy env (e.g. ALLOWED_HOSTS="your-app.onrender.com")
if ALLOWED_HOSTS == ["*"]:
    ALLOWED_HOSTS = []

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "15552000"))  # ≥180d (§4.4)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
