from fastapi.testclient import TestClient
import os
import tempfile
import pytest
import backend.database as database

@pytest.fixture(autouse=True)
def patch_duckdb_path(monkeypatch):
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as tf:
        db_path = tf.name
    # At this point, the file exists, so delete it so DuckDB can create it
    if os.path.exists(db_path):
        os.remove(db_path)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    # Import app after patching DB_PATH
    global app
    from backend.main import app as fastapi_app
    app = fastapi_app
    database.init_user_profile_storage()
    yield
    if os.path.exists(db_path):
        os.remove(db_path)

def test_stripe_create_session():
    with TestClient(app) as client:
        resp = client.post("/api/stripe/create-session", params={"user_id": "testuser", "plan": "pro"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "testuser"
        assert data["plan"] == "pro"
        assert data["status"] == "created"
        assert "session_id" in data

def test_stripe_webhook_triggers_plan_change():
    with TestClient(app) as client:
        # Create user profile first
        client.put("/api/user/profile", params={"user_id": "stripeuser", "plan": "free"})
        # Simulate Stripe webhook event
        event = {
            "type": "checkout.session.completed",
            "data": {"user_id": "stripeuser", "plan": "pro"}
        }
        resp = client.post("/api/stripe/webhook", json=event)
        assert resp.status_code == 200
        assert resp.json()["status"] == "plan changed"
        import time
        time.sleep(0.1)
        # Check user profile updated
        resp = client.get("/api/user/profile", params={"user_id": "stripeuser"})
        profile = resp.json()
        if resp.status_code == 200:
            assert profile["plan"] == "pro"
        else:
            assert False, f"Failed to fetch user profile: {profile}"
