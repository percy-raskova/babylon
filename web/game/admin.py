"""Admin registration for game models."""

from __future__ import annotations

from django.contrib import admin

from .models import ActionResult, GameSession, PlayerAction

admin.site.register(GameSession)
admin.site.register(PlayerAction)
admin.site.register(ActionResult)
