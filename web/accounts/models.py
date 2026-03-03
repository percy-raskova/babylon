"""Player profile model extending Django's auth User.

PlayerProfile is a managed model — Django owns its migrations.
It extends the built-in User with game-specific fields.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class PlayerProfile(models.Model):
    """Game-specific profile linked to a Django auth User.

    One-to-one extension of ``django.contrib.auth.models.User``.
    Stores display name and beta access flag for access control.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="player_profile",
    )
    display_name = models.CharField(max_length=64, blank=True, default="")
    is_beta_tester = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "player_profile"

    def __str__(self) -> str:
        return f"PlayerProfile({self.user_id}, {self.display_name!r})"
