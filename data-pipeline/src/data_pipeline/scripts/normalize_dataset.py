from __future__ import annotations

import shutil
from pathlib import Path

CANONICAL_DIR = Path("data/lennys-newsletterpodcastdata")


def _is_valid_dataset_dir(path: Path) -> bool:
    return (
        (path / "index.json").exists()
        and (path / "newsletters").is_dir()
        and (path / "podcasts").is_dir()
    )


def _find_candidate_dataset() -> Path | None:
    data_dir = Path("data")
    if not data_dir.exists():
        return None
    for child in data_dir.iterdir():
        if child == CANONICAL_DIR:
            continue
        if child.is_dir() and _is_valid_dataset_dir(child):
            return child
    return None


def main() -> None:
    if _is_valid_dataset_dir(CANONICAL_DIR):
        print(f"[ok] canonical dataset already available at {CANONICAL_DIR}")
        return

    source = _find_candidate_dataset()
    if source is None:
        raise FileNotFoundError(
            "Could not locate a dataset directory containing index.json + newsletters + podcasts."
        )

    CANONICAL_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, CANONICAL_DIR, dirs_exist_ok=True)
    print(f"[ok] copied dataset from {source} to {CANONICAL_DIR}")


if __name__ == "__main__":
    main()
