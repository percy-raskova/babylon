"""Admin registration for accounts models."""

from __future__ import annotations

from django.contrib import admin

from .models import PlayerProfile

admin.site.register(PlayerProfile)
