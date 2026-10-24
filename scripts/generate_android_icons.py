"""Generate Android launcher icons from apps/web/android/icm.jpg (or icl.jpg / icn.jpg)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ANDROID_DIR = ROOT / "apps" / "web" / "android"
ICON_CANDIDATES = ("icl.jpg", "icm.jpg", "icn.jpg", "ic.jpg")


def resolve_source_icon() -> Path:
    for name in ICON_CANDIDATES:
        path = ANDROID_DIR / name
        if path.exists():
            return path
    raise SystemExit(
        f"No icon source found in {ANDROID_DIR}. Add icm.jpg (or icl.jpg)."
    )


SOURCE = resolve_source_icon()
RES = ROOT / "apps" / "web" / "android" / "app" / "src" / "main" / "res"

LAUNCHER_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

FOREGROUND_SIZES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def square_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def save_launcher(image: Image.Image, path: Path, size: int) -> None:
    icon = square_crop(image).resize((size, size), Image.Resampling.LANCZOS)
    icon.save(path, format="PNG", optimize=True)


def save_foreground(image: Image.Image, path: Path, size: int) -> None:
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    target = int(size * 0.78)
    foreground = square_crop(image).resize((target, target), Image.Resampling.LANCZOS)
    offset = (size - target) // 2
    canvas.paste(foreground, (offset, offset))
    canvas.save(path, format="PNG", optimize=True)


def main() -> None:
    source_path = resolve_source_icon()
    source = Image.open(source_path).convert("RGBA")

    for folder, size in LAUNCHER_SIZES.items():
        target_dir = RES / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        save_launcher(source, target_dir / "ic_launcher.png", size)
        save_launcher(source, target_dir / "ic_launcher_round.png", size)

    for folder, size in FOREGROUND_SIZES.items():
        target_dir = RES / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        save_foreground(source, target_dir / "ic_launcher_foreground.png", size)

    print(f"Generated launcher icons from {source_path}")


if __name__ == "__main__":
    main()
