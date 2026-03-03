"""Admin registration for game models."""

from __future__ import annotations

from django.contrib import admin

from .models import ActionResult, GameEventLog, GameSession, PlayerAction

admin.site.register(GameSession)
admin.site.register(PlayerAction)
admin.site.register(ActionResult)


@admin.register(GameEventLog)
class GameEventLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-only admin view for the game event audit log."""

    list_display = ("timestamp", "category", "session_id", "user_id", "tick", "message")
    list_filter = ("category", "timestamp")
    search_fields = ("message", "session_id", "correlation_id")
    readonly_fields = (
        "timestamp",
        "category",
        "session_id",
        "user_id",
        "tick",
        "message",
        "details",
        "correlation_id",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, _request: object) -> bool:
        """Audit logs are created programmatically, not via admin."""
        return False

    def has_change_permission(self, _request: object, _obj: object = None) -> bool:
        """Audit logs are immutable."""
        return False

    def has_delete_permission(self, _request: object, _obj: object = None) -> bool:
        """Audit logs should not be deleted via admin."""
        return False
