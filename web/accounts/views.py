"""Authentication views for session-based login/logout.

No self-registration — admin creates accounts for beta testers.
"""

from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponseBase, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST


def login_page(request: HttpRequest) -> HttpResponseBase:
    """Render the login form (GET) or process login (POST)."""
    if request.method == "POST":
        return _handle_login(request)
    return render(request, "accounts/login.html")


def _handle_login(request: HttpRequest) -> JsonResponse:
    """Process a login form submission."""
    username = request.POST.get("username", "")
    password = request.POST.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({"status": "ok", "data": {"username": getattr(user, "username", "")}})
    return JsonResponse(
        {"status": "error", "message": "Invalid credentials"},
        status=401,
    )


@require_POST
def logout_view(request: HttpRequest) -> JsonResponse:
    """Log the user out and return confirmation."""
    logout(request)
    return JsonResponse({"status": "ok", "data": {"message": "Logged out"}})


@require_GET
def whoami(request: HttpRequest) -> JsonResponse:
    """Return the current user's identity or anonymous status."""
    if request.user.is_authenticated:
        return JsonResponse(
            {
                "status": "ok",
                "data": {
                    "id": request.user.pk,
                    "username": request.user.username,
                    "is_authenticated": True,
                },
            }
        )
    return JsonResponse(
        {
            "status": "ok",
            "data": {"is_authenticated": False},
        }
    )
