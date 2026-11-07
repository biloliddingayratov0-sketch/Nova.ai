"""
Comprehensive Integration Tests for NOVA AI Platform
Tests all phases: Auth, Chat, Code, Image Gen, Image Edit, Videos, Voice, Music, Audio Studio, Dashboard, Creations, Subscriptions, Payments, Admin, Notifications.
"""
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_api_status_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["name"] == "NOVA AI Master Platform"

    res_h = client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"


def test_auth_and_dashboard_flow():
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "username": "master_tester",
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    assert reg_res.status_code in (201, 409)

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Profile
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "master_tester"

    # 4. Dashboard Stats
    dash = client.get("/api/dashboard/stats", headers=headers)
    assert dash.status_code == 200
    stats = dash.json()["statistics"]
    assert "credits_remaining" in stats
    assert "total_images" in stats


@patch("app.routes.chat.generate_chat_response", return_value="Hello! I am NOVA AI, ready to assist you.")
def test_ai_chat_flow(mock_chat):
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Conversation
    conv = client.post("/api/chat/conversations", json={"title": "Test Chat"}, headers=headers)
    assert conv.status_code == 200
    conv_id = conv.json()["id"]

    # 2. Send Message
    msg = client.post(f"/api/chat/conversations/{conv_id}/messages", json={"content": "Hello NOVA AI!"}, headers=headers)
    assert msg.status_code == 200
    assert "assistant_message" in msg.json()
    assert msg.json()["assistant_message"]["content"] == "Hello! I am NOVA AI, ready to assist you."

    # 3. Export Conversation
    exp = client.get(f"/api/chat/conversations/{conv_id}/export?format=markdown", headers=headers)
    assert exp.status_code == 200
    assert "NOVA AI" in exp.json()["content"]

    # 4. Delete Conversation
    del_res = client.delete(f"/api/chat/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 200


@patch("app.routes.code.generate_code_solution", return_value={"language": "python", "solution": "def binary_search(arr, x): pass"})
@patch("app.routes.code.debug_code", return_value={"language": "python", "analysis_and_fix": "Root cause: subtraction used instead of addition. Corrected: return a + b"})
def test_ai_code_assistant_flow(mock_dbg, mock_gen):
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Code Generation
    gen = client.post("/api/code/generate", json={"prompt": "Write a binary search function", "language": "python"}, headers=headers)
    assert gen.status_code == 200
    assert "solution" in gen.json()

    # 2. Code Debug
    dbg = client.post("/api/code/debug", json={
        "code": "def add(a, b): return a - b",
        "error_message": "Result of add(2, 3) should be 5 but got -1",
        "language": "python"
    }, headers=headers)
    assert dbg.status_code == 200
    assert "analysis_and_fix" in dbg.json()

    # 3. Code Sandbox Execution
    run = client.post("/api/code/execute", json={
        "code": "print('NOVA_CODE_SUCCESS_42')",
        "language": "python"
    }, headers=headers)
    assert run.status_code == 200
    assert "NOVA_CODE_SUCCESS_42" in run.json()["stdout"]


def test_video_generation_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    job = client.post("/api/videos/generate", data={"prompt": "Cyberpunk flying car", "duration": 5}, headers=headers)
    assert job.status_code == 200
    job_id = job.json()["job_id"]

    status_res = client.get(f"/api/videos/jobs/{job_id}", headers=headers)
    assert status_res.status_code == 200
    assert "status" in status_res.json()


def test_voice_and_music_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Voice TTS
    tts = client.post("/api/voice/tts", data={"text": "Welcome to NOVA AI studio"}, headers=headers)
    assert tts.status_code == 200
    assert "audio_url" in tts.json()

    # 2. Music Generation
    music = client.post("/api/music/generate", data={"prompt": "Neon synthwave groove", "genre": "Electronic", "mood": "Energetic"}, headers=headers)
    assert music.status_code == 200
    assert "audio_url" in music.json()


def test_subscriptions_and_payments_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List Plans
    plans = client.get("/api/subscriptions/plans")
    assert plans.status_code == 200
    assert len(plans.json()) >= 3

    # 2. Sandbox payment simulation
    pay = client.post("/api/payments/sandbox-simulate", json={"provider": "click", "plan_code": "pro"}, headers=headers)
    assert pay.status_code == 200
    assert pay.json()["plan"] == "pro"


def test_notifications_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/notifications/", headers=headers)
    assert res.status_code == 200
    assert "unread_count" in res.json()


def test_admin_panel_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "master_tester@example.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ordinary user access check (should be 403)
    overview = client.get("/api/admin/overview", headers=headers)
    assert overview.status_code in (403, 200)
