from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def auth_headers():
    res = client.post("/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_client_bank_invoice_flow():
    headers = auth_headers()
    c = client.post("/api/v1/clients", headers=headers, json={"name": "Acme Pvt Ltd", "client_type": "contract", "country": "India", "tax_id": "GSTIN123"})
    assert c.status_code == 200
    client_id = c.json()["id"]

    b = client.post("/api/v1/banks", headers=headers, json={"account_holder_name": "Bharat", "bank_name": "SBI", "account_number": "123456789", "ifsc_code": "SBIN0000001"})
    assert b.status_code == 200
    bank_id = b.json()["id"]

    inv = client.post("/api/v1/invoices", headers=headers, json={"invoice_number": "INV-TEST-001", "client_id": client_id, "bank_account_id": bank_id, "subtotal": "1000.00", "tax_amount": "180.00", "invoice_format": "contract"})
    assert inv.status_code in (200, 400)  # 400 if rerun with same invoice number
    if inv.status_code == 200:
        assert inv.json()["total_amount"] == "1180.00"
