from __future__ import annotations

import importlib.util
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

# Only plugins shipped with this release may be loaded from disk.
ALLOWED_PLUGIN_STEMS = frozenset({
    "phasmopobia_plugin",
    "route_recorder_plugin",
    "input_humanization_plugin",
    "preset_benchmark_plugin",
    "example_plugin",
})

_MAX_PLUGIN_ID_LEN = 64
_MAX_PLUGIN_NAME_LEN = 120
_MAX_DESCRIPTION_LEN = 500


@dataclass
class PluginRecord:
    plugin_id: str
    name: str
    version: str
    description: str
    file_path: str
    loaded: bool
    error: str = ""


class PluginManager:
    """Discovers and loads local plugins from plugins/registry/."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.plugins_dir = self.project_root / "plugins"
        self.registry_dir = self.plugins_dir / "registry"
        self._records: list[PluginRecord] = []
        self._modules: dict[str, ModuleType] = {}

    def load_all(self) -> list[PluginRecord]:
        self._records = []
        self._modules = {}
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        for file_path in sorted(self.registry_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue
            if file_path.stem not in ALLOWED_PLUGIN_STEMS:
                continue
            rec = self._load_one(file_path)
            self._records.append(rec)
        return list(self._records)

    def records(self) -> list[PluginRecord]:
        return list(self._records)

    def summary(self) -> dict[str, int]:
        total = len(self._records)
        loaded = len([r for r in self._records if r.loaded])
        failed = total - loaded
        return {"total": total, "loaded": loaded, "failed": failed}

    @staticmethod
    def _validate_register_result(info: dict, default_id: str) -> tuple[str, str, str, str]:
        plugin_id = str(info.get("id", default_id)).strip() or default_id
        if len(plugin_id) > _MAX_PLUGIN_ID_LEN or not plugin_id.replace("_", "").isalnum():
            raise ValueError("Invalid plugin id.")
        name = str(info.get("name", plugin_id)).strip() or plugin_id
        if len(name) > _MAX_PLUGIN_NAME_LEN:
            name = name[:_MAX_PLUGIN_NAME_LEN]
        version = str(info.get("version", "0.1.0")).strip() or "0.1.0"
        description = str(info.get("description", "No description.")).strip()
        if len(description) > _MAX_DESCRIPTION_LEN:
            description = description[:_MAX_DESCRIPTION_LEN] + "…"
        return plugin_id, name, version, description

    def _load_one(self, file_path: Path) -> PluginRecord:
        default_id = file_path.stem
        try:
            resolved = file_path.resolve()
            registry_resolved = self.registry_dir.resolve()
            if registry_resolved not in resolved.parents:
                raise ValueError("Plugin path escapes registry directory.")

            module_name = f"mta_plugin_{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, str(resolved))
            if spec is None or spec.loader is None:
                return PluginRecord(
                    plugin_id=default_id,
                    name=default_id,
                    version="0.0.0",
                    description="Invalid module spec.",
                    file_path=str(file_path),
                    loaded=False,
                    error="Unable to create module spec.",
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            register = getattr(module, "register", None)
            if not callable(register):
                return PluginRecord(
                    plugin_id=default_id,
                    name=default_id,
                    version="0.0.0",
                    description="No register(context) function found.",
                    file_path=str(file_path),
                    loaded=False,
                    error="register(context) missing",
                )

            context = {
                "project_root": str(self.project_root),
                "plugins_dir": str(self.plugins_dir),
            }
            info = register(context)
            if not isinstance(info, dict):
                raise TypeError("register(context) must return a dict")

            plugin_id, name, version, description = self._validate_register_result(info, default_id)
            rec = PluginRecord(
                plugin_id=plugin_id,
                name=name,
                version=version,
                description=description,
                file_path=str(file_path),
                loaded=True,
                error="",
            )
            self._modules[plugin_id] = module
            return rec
        except Exception as exc:
            return PluginRecord(
                plugin_id=default_id,
                name=default_id,
                version="0.0.0",
                description="Plugin failed to load.",
                file_path=str(file_path),
                loaded=False,
                error=f"{exc}\n{traceback.format_exc(limit=2)}",
            )
