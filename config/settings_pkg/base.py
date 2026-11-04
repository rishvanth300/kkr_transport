"""Base settings for TCMS — shared by local and production.

Ref: SRS §2.5, §2.7, §4, §5.1, §5.6 (NFR-MAIN-001/002/003).
SRS modules mapped to Django apps:
  M-01/M-02 accounts | M-03/M-04 fleet | M-05 trips | M-06 dashboard
  M-07 reports       | M-08 accounts (audit) | M-09 admin | M-10 docs/scripts
Structure only — no module logic yet (see docs/STRUCTURE.md).
"""

import os
from pathlib import Path

# BASE_DIR = project root (folder containing manage.py), per NFR-MAIN-001.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:  # pragma: no cover
    pass

try:
    import dj_database_url
except Exception:  # pragma: no cover - lazy import in CI check
    dj_database_url = None

# --- Core ---------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# --- Apps (SRS §2.7 / §5.6: accounts, fleet, trips, reports, dashboard) --
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "axes",
    "whitenoise.runserver_nostatic",
]
LOCAL_APPS = [
    "accounts",
    "fleet",
    "trips",
    "reports",
    "dashboard",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware (SRS FR-AUTH-003, FR-ADM-003 security headers) ------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database: PostgreSQL only (SRS §2.5/§4.3, FR-ADM-003) ---------------
# Local: DATABASE_URL=postgres://user:pass@localhost:5432/kkr_transport
# Prod:  Neon/Supabase SSL connection string (dj-database-url parses it).
# SQLite is the fallback ONLY when DATABASE_URL is unset, so `check` works offline.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    if dj_database_url is None:
        raise RuntimeError("DATABASE_URL set but dj-database-url is not installed")
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Auth: roles admin/office/driver (SRS FR-USR-001, FR-AUTH-005) -------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "auth.User"  # profile/role app lands in Module 1 (accounts)
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# django-axes requires its backend (axes 7.x renamed AxesModelBackend → AxesStandaloneBackend).
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# django-axes lockout: 5 failures → 15 min (FR-AUTH-002 / AC-01)
AXES_FAILURE_LIMIT = int(os.environ.get("AXES_FAILURE_LIMIT", "5"))
AXES_COOLOFF_TIME = int(os.environ.get("AXES_COOLOFF_TIME", "15"))

# --- Session cookies (FR-AUTH-003) ---------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("1", "true", "yes")
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() in ("1", "true", "yes")
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8h absolute

# --- Internationalisation (NFR-CMP-001: INR, dd-mm-yyyy, km/tons) ---------
LANGUAGE_CODE = "en-in"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# --- Static / media (NFR-PERF-003 WhiteNoise, no CDN) --------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# --- Security headers (FR-ADM-003, §4.4) ---------------------------------
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() in ("1", "true", "yes")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging (NFR-SEC-012: IDs only, ≤90d retention) ---------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "axes": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
