#!/usr/bin/env python3
"""Automated, idempotent installer for Image-to-Image / Photo Editing functionality.

Usage:
    python install_img2img.py --project copilot-app [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"


def copy_asset(src: Path, dst: Path, dry_run: bool = False):
    """Copy an asset file to destination directory."""
    if not src.exists():
        print(f"  [ERROR] Asset source missing: {src}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        shutil.copy2(src, dst)
        print(f"  [COPIED] {src.name} -> {dst}")
    else:
        print(f"  [DRY-RUN] Would copy {src.name} -> {dst}")


def install(project_dir: Path, dry_run: bool = False):
    api_dir = project_dir / "api"
    web_dir = project_dir / "web"

    if not api_dir.exists() or not web_dir.exists():
        print(f"Error: Project directory must contain 'api' and 'web' folders ({project_dir})")
        sys.exit(1)

    print(f"\nInstalling Image-to-Image capability into {project_dir} (dry_run={dry_run})...\n")

    # 1. Copy backend assets
    print("--- 1. Updating Backend Assets ---")
    copy_asset(
        ASSETS_DIR / "api/app/services/image_gen.py",
        api_dir / "app/services/image_gen.py",
        dry_run,
    )
    copy_asset(
        ASSETS_DIR / "api/app/routes/images.py",
        api_dir / "app/routes/images.py",
        dry_run,
    )
    copy_asset(
        ASSETS_DIR / "api/tests/test_image_gen.py",
        api_dir / "tests/test_image_gen.py",
        dry_run,
    )

    # 2. Copy frontend assets
    print("\n--- 2. Updating Frontend Assets ---")
    copy_asset(
        ASSETS_DIR / "web/lib/helpers.ts",
        web_dir / "lib/helpers.ts",
        dry_run,
    )
    copy_asset(
        ASSETS_DIR / "web/lib/api.ts",
        web_dir / "lib/api.ts",
        dry_run,
    )
    copy_asset(
        ASSETS_DIR / "web/hooks/use-chat.ts",
        web_dir / "hooks/use-chat.ts",
        dry_run,
    )
    copy_asset(
        ASSETS_DIR / "web/components/chat/generated-image-card.tsx",
        web_dir / "components/chat/generated-image-card.tsx",
        dry_run,
    )

    print("\n[DONE] Image-to-Image installation completed successfully!\n")


def main():
    parser = argparse.ArgumentParser(description="Install Image-to-Image into copilot project.")
    parser.add_argument("--project", default="copilot-app", help="Path to project directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    install(project_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
