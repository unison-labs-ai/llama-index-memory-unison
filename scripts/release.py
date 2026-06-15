#!/usr/bin/env python3
"""Release: build, publish to PyPI (idempotent — skips if the version is already
on PyPI), then git-tag and push.

Needs a PyPI token. Either configure ~/.pypirc, or:
    export TWINE_USERNAME=__token__
    export TWINE_PASSWORD=pypi-...
Then:
    python scripts/release.py
"""
import glob
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
text = (ROOT / "pyproject.toml").read_text()
name = re.search(r'(?m)^name = "([^"]+)"', text).group(1)
version = re.search(r'(?m)^version = "([^"]+)"', text).group(1)


def on_pypi(pkg: str, ver: str) -> bool:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=10) as r:
            return ver in json.load(r).get("releases", {})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    except Exception:
        return False


def run(*cmd: str) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


if on_pypi(name, version):
    print(f"{name}=={version} is already on PyPI — nothing to do.")
    sys.exit(0)

run(sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "build", "twine")
shutil.rmtree(ROOT / "dist", ignore_errors=True)
run(sys.executable, "-m", "build")
run(sys.executable, "-m", "twine", "upload", *glob.glob(str(ROOT / "dist" / "*")))

try:
    run("git", "tag", f"v{version}")
    run("git", "push", "origin", f"v{version}")
except subprocess.CalledProcessError:
    print(f"Published, but could not push tag v{version} — tag it manually.")
print(f"Released {name}=={version}.")
