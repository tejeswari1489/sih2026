import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert "version" in res.json()

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}

def test_patient_registration_and_login():
    reg_payload = {
        "name": "Ramesh Kumar Test",
        "age": 45,
        "gender": "Male",
        "contact": "9876543210",
        "preferred_language": "Hindi",
        "abha_id": "99-9999-9999-9999"
    }
    res = client.post("/patient/register", json=reg_payload)
    assert res.status_code in [200, 400]  # 400 if already exists

    # Login
    login_res = client.post("/patient/login", json={"identifier": "Ramesh Kumar Test"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "patient_id" in data
    assert data["name"] == "Ramesh Kumar Test"

def test_staff_login():
    # Login as default seeded doctor
    res = client.post("/auth/staff/login", json={"username": "dr.sharma", "password": "doctor123"})
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    assert token_data["staff"]["role"] == "doctor"

    token = token_data["access_token"]
    # Access protected /auth/staff/me
    me_res = client.get("/auth/staff/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "dr.sharma"

def test_patient_otp_flow():
    otp_res = client.post("/auth/patient/send-otp", json={"identifier": "9876500001"})
    assert otp_res.status_code == 200
    data = otp_res.json()
    assert "demo_otp" in data

    verify_res = client.post("/auth/patient/verify-otp", json={"identifier": "9876500001", "otp": data["demo_otp"]})
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert "access_token" in verify_data
    assert "patient" in verify_data

def test_doctor_queue():
    res = client.get("/doctor/queue")
    assert res.status_code == 200
    assert "queue" in res.json()
    assert "total" in res.json()


def test_admin_analytics():
    res = client.get("/admin/analytics")
    assert res.status_code == 200
    data = res.json()
    assert "total_patients" in data
    assert "active_queue" in data
    assert "urgent_percentage" in data
    assert "departments" in data
    assert "languages" in data


def test_admin_staff_management_rbac():
    # 1. Login as Admin
    admin_login = client.post("/auth/staff/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List staff
    staff_res = client.get("/admin/staff")
    assert staff_res.status_code == 200
    staff_list = staff_res.json()
    assert len(staff_list) >= 3

    # 3. Create a test doctor
    create_payload = {
        "name": "Dr. Pytest Unit",
        "username": "dr.pytest.unit",
        "password": "pass12345password",
        "role": "doctor",
        "department": "Cardiology"
    }
    create_res = client.post("/admin/staff", json=create_payload, headers=headers)
    assert create_res.status_code in [200, 400]
    
    if create_res.status_code == 200:
        new_staff_id = create_res.json()["staff_id"]
        # 4. Delete the test doctor
        del_res = client.delete(f"/admin/staff/{new_staff_id}", headers=headers)
        assert del_res.status_code == 200


def test_attachment_upload():
    import io
    fake_img = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
    files = {"file": ("wound_test.png", fake_img, "image/png")}
    res = client.post("/chat/upload-attachment", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "url" in data
    assert data["url"].startswith("/uploads/")

