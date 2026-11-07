"""gh-pages publish rebases onto a moved remote and retries the push."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from publish_data import commit, copy_payload, publish, push_with_retry


def git(cwd, *args, check=True):
    proc = subprocess.run(
        ["git", "-c", "user.name=FOMO Test", "-c", "user.email=test@example.com", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc


class PublishTests(unittest.TestCase):
    def test_dry_run_does_not_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<p>world</p>\n")
            (root / "data").mkdir()
            (root / "data" / "ideas.json").write_text("{}\n")
            result = publish(root=root, remote=str(root / "missing.git"), dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertIn("index.html", result["files"])
            self.assertFalse((root / "missing.git").exists())

    def test_rebase_keeps_publisher_json_and_remote_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare = root / "bare.git"
            src = root / "src"
            other = root / "other"
            work = root / "work"
            git(None, "init", "--bare", "-b", "gh-pages", str(bare))
            src.mkdir()
            (src / "data").mkdir()
            (src / "index.html").write_text("<p>world</p>\n")
            (src / "data" / "ideas.json").write_text(json.dumps({"ideas": ["v1"]}) + "\n")
            first = publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            self.assertTrue(first["ok"])
            self.assertIsNotNone(first["published"])
            git(None, "clone", str(bare), str(other))
            (other / "NOTE").write_text("from the other side\n")
            git(other, "add", "NOTE")
            git(other, "commit", "-m", "remote moved")
            git(other, "push", "origin", "HEAD:gh-pages")
            (src / "data" / "ideas.json").write_text(json.dumps({"ideas": ["v2"]}) + "\n")
            copy_payload(src, work)
            self.assertTrue(commit(work, "stale ideas commit"))
            push_with_retry(work, "gh-pages")
            check = root / "check"
            git(None, "clone", str(bare), str(check))
            self.assertIn("v2", (check / "data" / "ideas.json").read_text())
            self.assertIn("other side", (check / "NOTE").read_text())

    def test_second_publish_fast_forwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare = root / "bare.git"
            src = root / "src"
            other = root / "other"
            work = root / "work"
            git(None, "init", "--bare", "-b", "gh-pages", str(bare))
            src.mkdir()
            (src / "index.html").write_text("ok\n")
            (src / "data").mkdir()
            (src / "data" / "ideas.json").write_text("{}\n")
            publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            git(None, "clone", str(bare), str(other))
            (other / "EXTRA").write_text("kept\n")
            git(other, "add", "EXTRA")
            git(other, "commit", "-m", "extra")
            git(other, "push", "origin", "HEAD:gh-pages")
            (src / "data" / "ideas.json").write_text('{"ideas":[1]}\n')
            result = publish(root=src, remote=str(bare), work=work, branch="gh-pages")
            self.assertTrue(result["published"])
            check = root / "check"
            git(None, "clone", str(bare), str(check))
            self.assertIn("ideas", (check / "data" / "ideas.json").read_text())
            self.assertEqual((check / "EXTRA").read_text(), "kept\n")


if __name__ == "__main__":
    unittest.main()
