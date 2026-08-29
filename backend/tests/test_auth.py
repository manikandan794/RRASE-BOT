from app.models import Role, RoleName


def _seed_roles(db):
    for name in (RoleName.STUDENT, RoleName.FACULTY, RoleName.ADMIN, RoleName.PRINCIPAL):
        db.add(Role(name=name, description=name))
    db.commit()


def test_register_and_login(client, test_db_session):
    _seed_roles(test_db_session)

    resp = client.post("/api/v1/auth/register", json={
        "email": "alice@example.edu", "full_name": "Alice", "password": "supersecret123",
    })
    assert resp.status_code == 201
    assert resp.json()["roles"] == [RoleName.STUDENT]

    resp = client.post("/api/v1/auth/login", json={
        "email": "alice@example.edu", "password": "supersecret123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["roles"] == [RoleName.STUDENT]


def test_login_rejects_wrong_password(client, test_db_session):
    _seed_roles(test_db_session)
    client.post("/api/v1/auth/register", json={
        "email": "bob@example.edu", "full_name": "Bob", "password": "correcthorsebattery",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "bob@example.edu", "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_student_cannot_create_department(client, test_db_session):
    _seed_roles(test_db_session)
    client.post("/api/v1/auth/register", json={
        "email": "carol@example.edu", "full_name": "Carol", "password": "supersecret123",
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "carol@example.edu", "password": "supersecret123",
    }).json()
    token = login["access_token"]

    resp = client.post(
        "/api/v1/departments",
        json={"name": "Electronics and Communication Engineering"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_admin_can_create_department(client, test_db_session):
    _seed_roles(test_db_session)
    admin_role = test_db_session.query(Role).filter_by(name=RoleName.ADMIN).first()
    from app.auth.security import hash_password
    from app.models import User, UserRole

    admin = User(email="admin@example.edu", full_name="Admin", hashed_password=hash_password("adminpass123"))
    test_db_session.add(admin)
    test_db_session.flush()
    test_db_session.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db_session.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "admin@example.edu", "password": "adminpass123",
    }).json()
    token = login["access_token"]

    resp = client.post(
        "/api/v1/departments",
        json={"name": "Electronics and Communication Engineering", "short_code": "ECE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["short_code"] == "ECE"
