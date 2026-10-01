import secrets
import uuid

from fastapi import HTTPException, Request, status


def require_admin(request: Request) -> None:
    """Allow an admin page only for a logged-in administrator."""
    if request.session.get("is_admin") is not True:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )


def csrf_token(request: Request) -> str:
    """Return a stable CSRF token for the current session."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, token: str | None) -> None:
    """Validate a token sent by an admin HTML form."""
    expected = request.session.get("csrf_token")
    if not token or not expected or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный CSRF-токен")


def ensure_session_csrf(request: Request) -> str:
    """Create a token on pages containing a form."""
    return csrf_token(request)
