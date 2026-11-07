#!/usr/bin/env python3
"""Publish the static site and data JSON to the gh-pages branch.

Same shape as Trenchfloor's publisher: existing git credentials, no tokens
on the command line, rebase-and-retry if the remote moved. A rejected auth
error is not retried.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PUBLIC = "https://joeypbrrr.github.io/fomo-world/"
SITE_FILES = [
    "index.html",
    "top10.html",
    "launch.html",
    "favicon.svg",
    ".nojekyll",
    "css/site.css",
    "js/agents.js",
    "js/art.js",
    "js/cards.js",
    "js/data.js",
    "js/launch.js",
    "js/scan.js",
    "js/top10.js",
    "js/world.js",
    "data/ideas.json",
    "data/image_queue.json",
    "data/example-ideas.json",
]
SITE_DIRS = ["images", "vendor"]
TOKEN_RE = re.compile(r"(https?://)([^/\s@]+)@")


def redact(text: str | None) -> str:
    return TOKEN_RE.sub(r"\1", text or "")


def git(cwd, *args, timeout=120, check=False):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(redact((proc.stderr or proc.stdout or "git failed").strip()))
    return proc


def commit(cwd, message: str) -> bool:
    git(cwd, "add", "-A")
    if git(cwd, "diff", "--cached", "--quiet").returncode == 0:
        return False
    proc = git(
        cwd,
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "commit", "-m", message,
    )
    if proc.returncode != 0:
        raise RuntimeError(redact(proc.stderr or proc.stdout or "commit failed"))
    return True


def remote_has_branch(remote: str, branch: str) -> bool:
    proc = git(None, "ls-remote", "--heads", remote, f"refs/heads/{branch}", timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("cannot read remote: " + redact(proc.stderr or proc.stdout))
    return bool(proc.stdout.strip())


def ensure_worktree(work: Path, remote: str, branch: str) -> str:
    if (work / ".git").exists():
        return "existing"
    if work.exists() and any(work.iterdir()):
        raise RuntimeError(f"{work} exists and is not a git checkout")
    if remote_has_branch(remote, branch):
        work.parent.mkdir(parents=True, exist_ok=True)
        proc = git(None, "clone", "--branch", branch, "--single-branch", remote, str(work), timeout=180)
        if proc.returncode != 0:
            raise RuntimeError("clone failed: " + redact(proc.stderr or proc.stdout))
        return "cloned"
    work.mkdir(parents=True, exist_ok=True)
    proc = git(None, "init", "-b", branch, str(work))
    if proc.returncode != 0:
        raise RuntimeError(redact(proc.stderr or proc.stdout))
    git(work, "remote", "add", "origin", remote, check=True)
    return "created"


def sync(work: Path, branch: str) -> None:
    fetched = git(work, "fetch", "origin", branch, timeout=120)
    if fetched.returncode != 0:
        text = (fetched.stderr or "").lower()
        if "couldn't find remote ref" in text or "not found" in text or "remote ref" in text:
            return
        raise RuntimeError("fetch failed: " + redact(fetched.stderr or fetched.stdout))
    if git(work, "rev-parse", "--verify", f"origin/{branch}").returncode != 0:
        return
    dirty = git(work, "status", "--porcelain")
    if dirty.stdout.strip():
        raise RuntimeError("publish worktree is dirty before sync; refusing to rebase over local edits")
    rebased = git(
        work,
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "rebase", f"origin/{branch}",
    )
    if rebased.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("sync rebase failed: " + redact(rebased.stderr or rebased.stdout))


def rebase_ours(work: Path, branch: str) -> None:
    fetched = git(work, "fetch", "origin", branch, timeout=120)
    if fetched.returncode != 0:
        raise RuntimeError("fetch during retry failed: " + redact(fetched.stderr or fetched.stdout))
    rebased = git(
        work,
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "rebase", "-X", "theirs", f"origin/{branch}",
    )
    if rebased.returncode == 0:
        return
    checkout = git(work, "checkout", "--theirs", "--", ".")
    if checkout.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("rebase conflict could not be resolved: " + redact(rebased.stderr or checkout.stderr))
    git(work, "add", "-A")
    continued = git(
        work,
        "-c", "core.editor=true",
        "-c", "user.name=joeypbrrr",
        "-c", "user.email=joeypbrrr@users.noreply.github.com",
        "rebase", "--continue",
    )
    if continued.returncode != 0:
        git(work, "rebase", "--abort")
        raise RuntimeError("rebase --continue failed: " + redact(continued.stderr or continued.stdout))


def push_with_retry(work: Path, branch: str, retries: int = 4) -> None:
    last = ""
    remote = git(work, "remote", "get-url", "origin", check=True).stdout.strip()
    for _attempt in range(retries):
        if remote_has_branch(remote, branch):
            git(
                work,
                "-c", "user.name=joeypbrrr",
                "-c", "user.email=joeypbrrr@users.noreply.github.com",
                "pull", "--rebase", "origin", branch,
                check=True,
            )
        proc = git(work, "push", "origin", f"HEAD:{branch}", timeout=180)
        if proc.returncode == 0:
            return
        last = redact(proc.stderr or proc.stdout)
        lowered = last.lower()
        if any(word in lowered for word in ("authentication", "permission", "403", "could not read")):
            raise RuntimeError(last)
        rebase_ours(work, branch)
    raise RuntimeError("push failed after rebase retries: " + last)


def _copy_file(root: Path, dest: Path, rel: str, copied: list[str]) -> None:
    src = root / rel
    if not src.is_file():
        return
    target = dest / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    copied.append(rel)


def copy_payload(root: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    for rel in SITE_FILES:
        _copy_file(root, dest, rel, copied)
    for rel in SITE_DIRS:
        src = root / rel
        if not src.is_dir():
            continue
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            if path.name == ".gitkeep":
                continue
            item = str(path.relative_to(root))
            _copy_file(root, dest, item, copied)
    ideas = dest / "data" / "ideas.json"
    if ideas.exists():
        try:
            raw = json.loads(ideas.read_text())
        except json.JSONDecodeError:
            raw = None
        if isinstance(raw, dict):
            raw["public_url"] = PUBLIC
            raw["last_published"] = datetime.now(ZoneInfo("America/New_York")).isoformat()
            ideas.write_text(json.dumps(raw, indent=2) + "\n")
    nojekyll = dest / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.write_text("")
        copied.append(".nojekyll")
    return copied


def publish(root=None, remote=None, branch="gh-pages", work=None, dry_run=False):
    root = Path(root or ROOT)
    if remote is None:
        remote = git(root, "remote", "get-url", "origin", check=True).stdout.strip()
    work = Path(work or (root / ".gh-pages"))
    if dry_run:
        files = [rel for rel in SITE_FILES if (root / rel).exists()]
        for rel in SITE_DIRS:
            base = root / rel
            if base.is_dir():
                files.extend(
                    str(path.relative_to(root))
                    for path in base.rglob("*")
                    if path.is_file() and path.name != ".gitkeep"
                )
        print("dry-run", len(files), "files")
        return {"ok": True, "dry_run": True, "files": files}
    ensure_worktree(work, remote, branch)
    if (work / ".git").exists() and git(work, "rev-parse", "--verify", "HEAD").returncode == 0:
        sync(work, branch)
    copied = copy_payload(root, work)
    stamp = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
    message = f"FOMO World publish {stamp}"
    if not commit(work, message):
        print("no new data")
        return {"ok": True, "published": None, "detail": "no new data", "files": copied}
    push_with_retry(work, branch)
    print("published", stamp, flush=True)
    return {"ok": True, "published": stamp, "files": copied}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publish FOMO World to gh-pages")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--branch", default="gh-pages")
    args = parser.parse_args(argv)
    try:
        result = publish(branch=args.branch, dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print("publish failed:", redact(str(exc))[:500], file=sys.stderr, flush=True)
        return 1
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
