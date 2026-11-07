#!/usr/bin/env python3
"""Copy finished coin logos into images/ and mark the queue done.

The owner's assistant (or any external generator) drops 1000x1000 PNGs in
the inbox. This script checks the PNG header, copies them to
images/<concept_id>.png, and updates data/image_queue.json.

Default inbox: /workspace/fomo-world/generated when that directory exists,
otherwise <repo>/generated.
"""

from __future__ import annotations

import argparse
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

from research.config import DEFAULT_IMAGE_INBOX, IMAGE_PX
from research.queue import load_queue, mark_done, write_queue

ROOT = Path(__file__).resolve().parent
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def default_inbox(root: Path = ROOT) -> Path:
    preferred = Path(DEFAULT_IMAGE_INBOX)
    if preferred.is_dir():
        return preferred
    return root / "generated"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_MAGIC:
        raise ValueError("not a PNG")
    if data[12:16] != b"IHDR":
        raise ValueError("missing IHDR")
    width, height = struct.unpack(">II", data[16:24])
    # CRC check on IHDR so a truncated header is rejected.
    expected = struct.unpack(">I", data[29:33])[0]
    actual = zlib.crc32(data[12:29]) & 0xFFFFFFFF
    if expected != actual:
        raise ValueError("bad IHDR checksum")
    return width, height


def import_images(src: Path, root: Path = ROOT, publish: bool = False) -> dict:
    src = Path(src)
    if not src.is_dir():
        raise RuntimeError(f"inbox not found: {src}")
    queue_path = root / "data" / "image_queue.json"
    queue = load_queue(queue_path)
    known = {item.get("concept_id") for item in queue.get("items") or []}
    images = root / "images"
    images.mkdir(parents=True, exist_ok=True)
    imported = []
    rejected = []
    unknown = []
    now = datetime.now(timezone.utc)
    for path in sorted(src.glob("*.png")):
        concept_id = path.stem
        try:
            width, height = png_size(path)
        except (OSError, ValueError) as exc:
            rejected.append({"file": path.name, "reason": str(exc)})
            continue
        if width != IMAGE_PX or height != IMAGE_PX:
            rejected.append({
                "file": path.name,
                "reason": f"{width}x{height}, expected {IMAGE_PX}x{IMAGE_PX}",
            })
            continue
        target = images / f"{concept_id}.png"
        target.write_bytes(path.read_bytes())
        if concept_id in known:
            mark_done(queue, concept_id, now=now)
            imported.append(concept_id)
        else:
            unknown.append(concept_id)
    write_queue(queue_path, queue)
    result = {"ok": True, "imported": imported, "rejected": rejected, "unknown": unknown}
    if publish and imported:
        from publish_data import publish as publish_site
        result["publish"] = publish_site(root=root)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import 1000x1000 coin PNGs into the site")
    parser.add_argument("--from", dest="src", default=None, help="Folder of <concept_id>.png files")
    parser.add_argument("--publish", action="store_true", help="Push the site to gh-pages after a successful import")
    args = parser.parse_args(argv)
    src = Path(args.src) if args.src else default_inbox()
    try:
        result = import_images(src, publish=args.publish)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print("import failed:", exc)
        return 1
    print(
        f"imported {len(result['imported'])} "
        f"rejected {len(result['rejected'])} "
        f"unknown {len(result['unknown'])}"
    )
    for item in result["rejected"]:
        print("reject", item["file"], item["reason"])
    for concept_id in result["unknown"]:
        print("unknown concept id (copied, queue unchanged)", concept_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
