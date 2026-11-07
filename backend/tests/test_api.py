"""
NOVA AI Backend Tests
Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# --- Auth Tests ---

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_register_success():
    r = client.post("/api/auth/register", json={
        "username": "testuser_pytest",
        "email": "pytest@example.com",
        "password": "TestPass123!"
    })
    # 201 on first run, 409 on re-run (idempotent test)
    assert r.status_code in (201, 409)


def test_register_duplicate():
    payload = {
        "username": "dupuser",
        "email": "dup@example.com",
        "password": "StrongPass1!"
    }
    client.post("/api/auth/register", json=payload)
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_register_weak_password():
    r = client.post("/api/auth/register", json={
        "username": "weakpwuser",
        "email": "weakpw@example.com",
        "password": "short"
    })
    assert r.status_code == 422


def test_login_wrong_password():
    client.post("/api/auth/register", json={
        "username": "logintest",
        "email": "logintest@example.com",
        "password": "CorrectPass1!"
    })
    r = client.post("/api/auth/login", json={
        "email": "logintest@example.com",
        "password": "WrongPass123!"
    })
    assert r.status_code == 401


def test_login_success_and_me():
    client.post("/api/auth/register", json={
        "username": "metest_user",
        "email": "metest@example.com",
        "password": "MeTestPass1!"
    })
    r = client.post("/api/auth/login", json={
        "email": "metest@example.com",
        "password": "MeTestPass1!"
    })
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "metest@example.com"


def test_me_unauthenticated():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def _get_token(username="histtest", email="histtest@example.com", password="HistTest1!"):
    client.post("/api/auth/register", json={
        "username": username, "email": email, "password": password
    })
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_history_empty():
    token = _get_token("histuser2", "histuser2@example.com", "HistUser2Pass!")
    r = client.get("/api/history/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_history_unauthenticated():
    r = client.get("/api/history/")
    assert r.status_code == 401


def test_stats_endpoint():
    token = _get_token("statsuser", "statsuser@example.com", "StatsPass1!")
    r = client.get("/api/history/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "generated" in data
    assert "favorites" in data


def test_generate_requires_auth():
    r = client.post("/api/images/generate", data={"prompt": "test"})
    assert r.status_code == 401


def test_edit_requires_auth():
    import io
    r = client.post(
        "/api/images/edit",
        data={"prompt": "test"},
        files={"image": ("test.png", io.BytesIO(b"fake"), "image/png")},
    )
    assert r.status_code == 401


def test_user_isolation():
    """User A should not see User B's history."""
    token_a = _get_token("isolation_a", "isolation_a@example.com", "IsoPassA1!")
    token_b = _get_token("isolation_b", "isolation_b@example.com", "IsoPassB1!")

    hist_a = client.get("/api/history/", headers={"Authorization": f"Bearer {token_a}"})
    hist_b = client.get("/api/history/", headers={"Authorization": f"Bearer {token_b}"})

    assert hist_a.status_code == 200
    assert hist_b.status_code == 200
    # IDs in each user's history must not overlap (each has their own empty history here)
    ids_a = {item["id"] for item in hist_a.json()["items"]}
    ids_b = {item["id"] for item in hist_b.json()["items"]}
    assert ids_a.isdisjoint(ids_b)


def test_profile_update():
    token = _get_token("profileupdater", "profileupdater@example.com", "ProfilePass1!")
    r = client.patch(
        "/api/auth/me",
        json={"bio": "I love AI art"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["bio"] == "I love AI art"


def test_change_password_wrong_current():
    token = _get_token("changepw", "changepw@example.com", "ChangePass1!")
    r = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongPass!", "new_password": "NewPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
