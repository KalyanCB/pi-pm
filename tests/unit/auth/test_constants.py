"""Unit tests for auth constants and password hashing."""
from app.auth.constants import Permission, UserRole, role_has_permission
from app.auth.password import hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("secure-password")
    assert verify_password("secure-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_owner_has_portfolio_write():
    assert role_has_permission(UserRole.OWNER, Permission.PORTFOLIO_WRITE)


def test_viewer_cannot_write_portfolio():
    assert not role_has_permission(UserRole.VIEWER, Permission.PORTFOLIO_WRITE)


def test_viewer_can_read_portfolio():
    assert role_has_permission(UserRole.VIEWER, Permission.PORTFOLIO_READ)


def test_admin_has_all_permissions():
    for perm in Permission:
        assert role_has_permission(UserRole.ADMIN, perm)
