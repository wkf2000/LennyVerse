from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.galaxy import GalaxySnapshotResponse


class GalaxySnapshotStore:
    def __init__(self, *, base_dir: Path) -> None:
        self._base_dir = base_dir

    def write(self, snapshot: GalaxySnapshotResponse) -> Path:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        version_path = self._base_dir / f"{snapshot.version}.json"
        latest_path = self._base_dir / "latest.json"
        payload = snapshot.model_dump(mode="json")
        serialized = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
        version_path.write_text(serialized, encoding="utf-8")
        latest_path.write_text(serialized, encoding="utf-8")
        return version_path
