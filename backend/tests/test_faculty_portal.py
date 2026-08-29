"""
Tests for CRITICAL FIX #3: faculty department-scoped authorization.

Verifies:
- a faculty member can manage FAQs/notices/department description for
  their OWN department only
- a faculty member cannot touch another department's records, even by
  supplying a different department_id in the request body
- an admin-only route (departments.py) is still closed to faculty
"""
from app.auth.security import hash_password
from app.models import Department, Faculty, Role, RoleName, User, UserRole


def _seed_roles(db):
    for name in (RoleName.STUDENT, RoleName.FACULTY, RoleName.ADMIN, RoleName.PRINCIPAL):
        db.add(Role(name=name, description=name))
    db.commit()


def _make_faculty_user(db, email, department_id):
    faculty_role = db.query(Role).filter_by(name=RoleName.FACULTY).first()
    user = User(email=email, full_name="Faculty Member", hashed_password=hash_password("facultypass123"))
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=faculty_role.id))
    db.add(Faculty(user_id=user.id, department_id=department_id, full_name="Faculty Member"))
    db.commit()
    return user


def _login(client, email):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "facultypass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_two_departments(db):
    dept_a = Department(name="Computer Science", short_code="CSE")
    dept_b = Department(name="Mechanical Engineering", short_code="MECH")
    db.add_all([dept_a, dept_b])
    db.commit()
    db.refresh(dept_a)
    db.refresh(dept_b)
    return dept_a, dept_b


def test_faculty_can_manage_own_department_faq(client, test_db_session):
    _seed_roles(test_db_session)
    dept_a, _dept_b = _seed_two_departments(test_db_session)
    _make_faculty_user(test_db_session, "cse.faculty@example.edu", dept_a.id)
    token = _login(client, "cse.faculty@example.edu")

    resp = client.post(
        "/api/v1/faculty/me/faqs",
        json={"question": "What labs does CSE have?", "answer": "Networking and AI labs.", "is_published": True},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["department_id"] == dept_a.id


def test_faculty_department_id_in_payload_is_ignored(client, test_db_session):
    """Even if the client sends a different department_id in the body, the
    record must be tagged with the faculty member's OWN department, never
    the client-supplied value."""
    _seed_roles(test_db_session)
    dept_a, dept_b = _seed_two_departments(test_db_session)
    _make_faculty_user(test_db_session, "cse.faculty2@example.edu", dept_a.id)
    token = _login(client, "cse.faculty2@example.edu")

    resp = client.post(
        "/api/v1/faculty/me/faqs",
        json={
            "department_id": dept_b.id,  # attempted spoof
            "question": "Spoofed question", "answer": "Spoofed answer", "is_published": True,
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["department_id"] == dept_a.id  # server-derived, not dept_b


def test_faculty_cannot_edit_another_departments_faq(client, test_db_session):
    _seed_roles(test_db_session)
    dept_a, dept_b = _seed_two_departments(test_db_session)
    _make_faculty_user(test_db_session, "cse.faculty3@example.edu", dept_a.id)
    _make_faculty_user(test_db_session, "mech.faculty@example.edu", dept_b.id)

    token_a = _login(client, "cse.faculty3@example.edu")
    created = client.post(
        "/api/v1/faculty/me/faqs",
        json={"question": "CSE-only FAQ", "answer": "CSE answer", "is_published": True},
        headers=_auth_headers(token_a),
    ).json()

    token_b = _login(client, "mech.faculty@example.edu")
    resp = client.put(
        f"/api/v1/faculty/me/faqs/{created['id']}",
        json={"question": "Hijacked", "answer": "Hijacked answer", "is_published": True},
        headers=_auth_headers(token_b),
    )
    assert resp.status_code == 403


def test_faculty_can_only_update_own_department_description(client, test_db_session):
    _seed_roles(test_db_session)
    dept_a, dept_b = _seed_two_departments(test_db_session)
    _make_faculty_user(test_db_session, "cse.faculty4@example.edu", dept_a.id)
    token = _login(client, "cse.faculty4@example.edu")

    resp = client.put(
        "/api/v1/faculty/me/department",
        json={"description": "Updated CSE department description."},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == dept_a.id
    assert resp.json()["description"] == "Updated CSE department description."

    test_db_session.refresh(dept_b)
    assert dept_b.description is None  # untouched


def test_faculty_still_cannot_reach_admin_department_route(client, test_db_session):
    _seed_roles(test_db_session)
    dept_a, _dept_b = _seed_two_departments(test_db_session)
    _make_faculty_user(test_db_session, "cse.faculty5@example.edu", dept_a.id)
    token = _login(client, "cse.faculty5@example.edu")

    resp = client.put(
        f"/api/v1/departments/{dept_a.id}",
        json={"name": "Renamed Department"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 403


def test_faculty_without_profile_gets_403_not_500(client, test_db_session):
    _seed_roles(test_db_session)
    faculty_role = test_db_session.query(Role).filter_by(name=RoleName.FACULTY).first()
    user = User(email="noprofile@example.edu", full_name="No Profile", hashed_password=hash_password("facultypass123"))
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UserRole(user_id=user.id, role_id=faculty_role.id))
    test_db_session.commit()

    token = _login(client, "noprofile@example.edu")
    resp = client.get("/api/v1/faculty/me/department", headers=_auth_headers(token))
    assert resp.status_code == 403
