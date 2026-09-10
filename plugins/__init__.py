"""
Future plugin system interface.

This module intentionally contains no heavy logic today — it only defines
the contract a future plugin (calculator, translator, web_search, weather,
github, cloudflare, reminders, moderation, ...) must implement so it can be
registered with the bot without touching core handler code.

A plugin is any object implementing the Plugin protocol below. Plugins are
expected to live in their own subpackage under plugins/<name>/ with a
`register(dispatcher)` entrypoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class Plugin(Protocol):
    name: str
    description: str

    def register(self, dispatcher) -> None:
        """Attach the plugin's aiogram Router(s) to the dispatcher."""
        ...


@dataclass
class PluginMetadata:
    name: str
    description: str
    enabled: bool = False


# Registry populated by future plugins. Left empty on purpose — enabling a
# plugin should never require editing core app/ code, just adding it here
# (or to a config-driven loader) once it exists.
AVAILABLE_PLUGINS: list[PluginMetadata] = [
    PluginMetadata(name="calculator", description="Evaluate math expressions safely"),
    PluginMetadata(name="translator", description="Dedicated translation plugin"),
    PluginMetadata(name="web_search", description="Web search augmented answers"),
    PluginMetadata(name="weather", description="Weather lookups"),
    PluginMetadata(name="github", description="GitHub repo/issue lookups"),
    PluginMetadata(name="cloudflare", description="Cloudflare account helpers"),
    PluginMetadata(name="reminders", description="User-set reminders"),
    PluginMetadata(name="moderation", description="Group moderation helpers"),
]
