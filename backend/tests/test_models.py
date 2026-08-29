from app.models import Role, RoleName, User, UserRole


def test_create_user_and_assign_role(test_db_session):
    role = Role(name=RoleName.STUDENT, description="Student role")
    test_db_session.add(role)
    test_db_session.commit()

    user = User(
        email="student@example.edu",
        full_name="Test Student",
        hashed_password="not-a-real-hash-placeholder",
    )
    test_db_session.add(user)
    test_db_session.commit()

    link = UserRole(user_id=user.id, role_id=role.id)
    test_db_session.add(link)
    test_db_session.commit()

    fetched = test_db_session.query(User).filter_by(email="student@example.edu").first()
    assert fetched is not None
    assert fetched.is_active is True
    assert len(fetched.user_roles) == 1
    assert fetched.user_roles[0].role.name == RoleName.STUDENT


def test_email_uniqueness_enforced(test_db_session):
    from sqlalchemy.exc import IntegrityError

    user1 = User(email="dup@example.edu", full_name="A", hashed_password="x")
    test_db_session.add(user1)
    test_db_session.commit()

    user2 = User(email="dup@example.edu", full_name="B", hashed_password="y")
    test_db_session.add(user2)
    try:
        test_db_session.commit()
        assert False, "Expected a uniqueness violation"
    except IntegrityError:
        test_db_session.rollback()
