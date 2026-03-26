from pathlib import Path
import uuid

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "storage" / "assets"

ASSET_DIR.mkdir(parents=True, exist_ok=True)


def make_asset_storage_path(asset_id: str) -> Path:
    return ASSET_DIR / f"{asset_id}.bin"