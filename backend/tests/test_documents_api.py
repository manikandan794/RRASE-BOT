"""
API-level test for CRITICAL FIX #1: a freshly uploaded document must stay
PENDING and unretrievable until an admin/principal explicitly approves it
via /documents/{id}/review.

PDF text extraction and the AI provider are mocked (same approach as
test_chat_service.py) so this test never needs a real PDF library call or
network access.
"""
import io
from unittest.mock import patch

from app.auth.security import hash_password
from app.models import KnowledgeChunk, Role, RoleName, User, UserRole
from app.models.knowledge import ApprovalStatus


def _seed_roles(db):
    for name in (RoleName.STUDENT, RoleName.FACULTY, RoleName.ADMIN, RoleName.PRINCIPAL):
        db.add(Role(name=name, description=name))
    db.commit()


def _make_admin(db):
    admin_role = db.query(Role).filter_by(name=RoleName.ADMIN).first()
    user = User(email="admin@example.edu", full_name="Admin", hashed_password=hash_password("adminpass123"))
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    db.commit()
    return user


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_upload_stays_pending_and_unembedded_until_reviewed(client, test_db_session, monkeypatch):
    _seed_roles(test_db_session)
    _make_admin(test_db_session)
    token = _login(client, "admin@example.edu", "adminpass123")

    monkeypatch.setattr(
        "app.api.v1.documents.extract_text",
        lambda path: ("The library is open 8 AM to 8 PM on all working days.", 1),
    )

    with patch("app.rag.indexer.get_provider_manager") as mock_manager_factory:
        # No embedding call should even happen at upload time.
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("handbook.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        mock_manager_factory.assert_not_called()

    assert resp.status_code == 200
    doc = resp.json()
    assert doc["status"] == "pending"

    chunks = test_db_session.query(KnowledgeChunk).filter_by(source_id=doc["id"]).all()
    assert len(chunks) > 0
    assert all(c.status == ApprovalStatus.PENDING and not c.embedded for c in chunks)

    # Approve it - only now should embedding happen and status flip.
    with patch("app.rag.indexer.get_provider_manager") as mock_manager_factory:
        mock_manager = mock_manager_factory.return_value
        mock_manager.embed.side_effect = lambda texts: ([[0.1] * 8 for _ in texts], "ollama")
        review_resp = client.post(
            f"/api/v1/documents/{doc['id']}/review",
            json={"approve": True},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"
    test_db_session.expire_all()
    chunks = test_db_session.query(KnowledgeChunk).filter_by(source_id=doc["id"]).all()
    assert all(c.status == ApprovalStatus.APPROVED and c.embedded for c in chunks)


def test_rejecting_a_document_deletes_its_staged_chunks(client, test_db_session, monkeypatch):
    _seed_roles(test_db_session)
    _make_admin(test_db_session)
    token = _login(client, "admin@example.edu", "adminpass123")

    monkeypatch.setattr(
        "app.api.v1.documents.extract_text",
        lambda path: ("Some draft content that should not be approved.", 1),
    )

    resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("draft.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    doc_id = resp.json()["id"]

    review_resp = client.post(
        f"/api/v1/documents/{doc_id}/review",
        json={"approve": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "rejected"
    assert test_db_session.query(KnowledgeChunk).filter_by(source_id=doc_id).count() == 0
