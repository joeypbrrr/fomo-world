"""Image prompt queue. Only new concept ids are inserted."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from research.config import IMAGE_PX


def empty_queue(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    return {
        "schema": "fomo-world.image-queue.v1",
        "updated_at": now.astimezone(timezone.utc).isoformat(),
        "note": (
            "Pending prompts are for an external assistant to draw. "
            "FOMO World does not call an image API and does not launch tokens."
        ),
        "items": [],
    }


def load_queue(path: Path) -> dict:
    if not path.exists():
        return empty_queue()
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return empty_queue()
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return empty_queue()
    return data


def merge_queue(existing: dict, ideas: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    stamp = now.astimezone(timezone.utc).isoformat()
    items = [dict(item) for item in existing.get("items") or [] if isinstance(item, dict) and item.get("concept_id")]
    by_id = {item["concept_id"]: item for item in items}
    for idea in ideas:
        concept_id = idea["id"]
        payload = {
            "concept_id": concept_id,
            "token_name": idea["token_name"],
            "ticker": idea["ticker"],
            "prompt": idea["image_prompt"],
            "target_width": IMAGE_PX,
            "target_height": IMAGE_PX,
            "format": "PNG",
            "status": "pending",
            "image_path": f"images/{concept_id}.png",
            "added_at": stamp,
            "completed_at": None,
        }
        current = by_id.get(concept_id)
        if current is None:
            items.append(payload)
            by_id[concept_id] = payload
            continue
        if current.get("status") == "pending":
            current["token_name"] = payload["token_name"]
            current["ticker"] = payload["ticker"]
            current["prompt"] = payload["prompt"]
            current["target_width"] = IMAGE_PX
            current["target_height"] = IMAGE_PX
        # done items keep their prompt and are not re-queued
    return {
        "schema": "fomo-world.image-queue.v1",
        "updated_at": stamp,
        "note": empty_queue()["note"],
        "items": items,
    }


def write_queue(path: Path, queue: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2) + "\n")


def mark_done(queue: dict, concept_id: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    found = False
    for item in queue.get("items") or []:
        if item.get("concept_id") == concept_id:
            item["status"] = "done"
            item["completed_at"] = now.astimezone(timezone.utc).isoformat()
            item["image_path"] = f"images/{concept_id}.png"
            found = True
    if found:
        queue["updated_at"] = now.astimezone(timezone.utc).isoformat()
    return found
