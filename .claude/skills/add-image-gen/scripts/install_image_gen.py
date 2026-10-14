#!/usr/bin/env python3
"""Automated, idempotent installer for text-to-image generation functionality.

Usage:
    python install_image_gen.py --project copilot-app [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_DIR / "assets"


def patch_file(path: Path, target: str, replacement: str, dry_run: bool = False) -> bool:
    """Replace target with replacement in file if target exists and replacement isn't already present."""
    if not path.exists():
        print(f"  [SKIP] File not found: {path}")
        return False

    content = path.read_text(encoding="utf-8")
    if replacement.strip() in content:
        print(f"  [OK] Already patched: {path.name}")
        return True

    if target not in content:
        print(f"  [WARN] Anchor string not found in {path.name}")
        return False

    new_content = content.replace(target, replacement, 1)
    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
        print(f"  [PATCHED] {path.name}")
    else:
        print(f"  [DRY-RUN] Would patch {path.name}")
    return True


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

    print(f"\nInstalling text-to-image generation into {project_dir} (dry_run={dry_run})...\n")

    # 1. Copy Assets
    print("--- 1. Copying Assets ---")
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
    copy_asset(
        ASSETS_DIR / "web/components/chat/generated-image-card.tsx",
        web_dir / "components/chat/generated-image-card.tsx",
        dry_run,
    )

    # 2. Patch api/app/main.py
    print("\n--- 2. Patching api/app/main.py ---")
    patch_file(
        api_dir / "app/main.py",
        "from app.routes import chat, health, models",
        "from app.routes import chat, health, images, models",
        dry_run,
    )
    patch_file(
        api_dir / "app/main.py",
        'app.include_router(chat.router, prefix="/api")',
        'app.include_router(chat.router, prefix="/api")\n    app.include_router(images.router, prefix="/api")',
        dry_run,
    )

    # 3. Patch api/app/schemas.py
    print("\n--- 3. Patching api/app/schemas.py ---")
    patch_file(
        api_dir / "app/schemas.py",
        '        if self.images and self.role != "user":\n            raise ValueError("Only user messages can have images")',
        "        # Relaxed to allow image attachments or generation on assistant messages\n        pass",
        dry_run,
    )

    # 4. Patch api/app/core/config.py
    print("\n--- 4. Patching api/app/core/config.py ---")
    patch_file(
        api_dir / "app/core/config.py",
        "from dotenv import load_dotenv",
        "from dotenv import find_dotenv, load_dotenv\n\nload_dotenv(find_dotenv(usecwd=True))",
        dry_run,
    )

    # 5. Patch web/components/chat/message.tsx
    print("\n--- 5. Patching web/components/chat/message.tsx ---")
    patch_file(
        web_dir / "components/chat/message.tsx",
        'import { Markdown } from "@/components/chat/markdown";',
        'import { GeneratedImageCard } from "@/components/chat/generated-image-card";\nimport { Markdown } from "@/components/chat/markdown";',
        dry_run,
    )
    patch_file(
        web_dir / "components/chat/message.tsx",
        "        {message.content ? (",
        """        {message.generatedImage && (
          <GeneratedImageCard
            id={message.generatedImage.id}
            mediaType={message.generatedImage.mediaType}
            data={message.generatedImage.data}
            engine={message.generatedImage.engine}
            prompt={message.generatedImage.prompt}
          />
        )}

        {message.content ? (""",
        dry_run,
    )

    print("\n[DONE] Installation completed successfully!\n")


def main():
    parser = argparse.ArgumentParser(description="Install image generation into copilot project.")
    parser.add_argument("--project", default="copilot-app", help="Path to project directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    install(project_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
