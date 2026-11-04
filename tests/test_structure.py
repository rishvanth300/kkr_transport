"""Structure smoke tests — verify skeleton wiring only (no module logic yet).

SRS AC-02 / NFR-MAIN-003 will land per-module; this file keeps the structure
PR green on CI before Module 1.
"""

from django.apps import apps


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_all_apps_importable():
    for label in ("accounts", "fleet", "trips", "dashboard", "reports"):
        assert apps.get_app_config(label)
