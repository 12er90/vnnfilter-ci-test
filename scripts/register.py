#!/usr/bin/env python3
"""Minimal stand-in for the real register.py — CI-wiring test only.

Installs one solvers/<id>/<version> directory in an isolated venv, asks
--name and --version, and prints one JSON line. Enough to prove the
GitHub Actions plumbing works; not the real vnnfilter collection logic.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def bin_dir(root: Path) -> Path:
    return root / ("Scripts" if os.name == "nt" else "bin")


def main():
    if len(sys.argv) != 2:
        print("usage: register.py solvers/<id>/<version>", file=sys.stderr)
        return 2

    solver_dir = Path(sys.argv[1]).resolve()
    version = solver_dir.name
    solver_id = solver_dir.parent.name
    script = solver_dir / "install.sh"

    work = Path(tempfile.mkdtemp(prefix=f"reg-{solver_id}-"))
    try:
        env_root = work / "env"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_root)
        bindir = bin_dir(env_root)

        env = dict(os.environ)
        env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
        env["SOLVER_BIN_DIR"] = str(bindir)

        proc = subprocess.run(
            ["bash", str(script)], cwd=solver_dir, env=env,
            capture_output=True, text=True, timeout=900,
        )
        if proc.returncode != 0:
            print(json.dumps({
                "id": solver_id, "version": version, "status": "install_failed",
                "error": (proc.stderr or proc.stdout).strip()[-500:],
            }))
            return 0

        binary = shutil.which(solver_id, path=str(bindir))
        if binary is None:
            print(json.dumps({
                "id": solver_id, "version": version, "status": "install_failed",
                "error": f"no executable named {solver_id!r} left on PATH",
            }))
            return 0

        name = subprocess.run([binary, "--name"], capture_output=True, text=True).stdout.strip()
        ver = subprocess.run([binary, "--version"], capture_output=True, text=True).stdout.strip()
        print(json.dumps({
            "id": solver_id, "version": version, "status": "ok",
            "reported_name": name, "reported_version": ver,
        }))
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
