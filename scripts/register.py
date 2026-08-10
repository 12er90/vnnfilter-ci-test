#!/usr/bin/env python3
"""Stand-in for the real register.py — CI-wiring test, extended to actually
call the `supports` interface (Section 5.4) instead of just --name/--version.

Still simplified relative to the real pipeline: theory fields are split into
identifier + note on ' * ' (vibecheck's own partial-support notation, not
part of the standard), but onnx-operators and the two boolean flags are kept
as raw lines rather than parsed, since their exact real-world formatting
hasn't been inspected from a live run yet. Don't assert a schema for output
nobody has actually seen.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

SUPPORTS_FLAGS = [
    "--onnx-opset-versions",
    "--onnx-element-types",
    "--onnx-operators",
    "--vnnlib-versions",
    "--hidden-node-theories",
    "--multiple-input-output-theories",
    "--multiple-network-theories",
    "--multiple-node-comparison-theories",
    "--arithmetic-complexity-theories",
    "--optimised-disjunctive-reasoning",
    "--serialise-assignments",
]

# Flags whose output is a theory-identifier list and may carry vibecheck's
# "IDENT * note" partial-support suffix.
THEORY_FLAGS = {
    "--hidden-node-theories",
    "--multiple-input-output-theories",
    "--multiple-network-theories",
    "--multiple-node-comparison-theories",
    "--arithmetic-complexity-theories",
}


def bin_dir(root: Path) -> Path:
    return root / ("Scripts" if os.name == "nt" else "bin")


def run(binary, *args):
    proc = subprocess.run([binary, *args], capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def split_theory_line(line):
    """'POLY * some note' -> ('POLY', 'some note'); 'POLY' -> ('POLY', None)."""
    if " * " in line:
        ident, note = line.split(" * ", 1)
        return ident.strip(), note.strip()
    return line.strip(), None


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

        errors = []
        _, name, err = run(binary, "--name")
        if err:
            errors.append(f"--name: {err[:200]}")
        _, ver, err = run(binary, "--version")
        if err:
            errors.append(f"--version: {err[:200]}")

        capabilities = {}
        partial_support = {}
        for flag in SUPPORTS_FLAGS:
            rc, out, err = run(binary, "supports", flag)
            key = flag.lstrip("-").replace("-", "_")
            if rc != 0:
                capabilities[key] = None
                errors.append(f"supports {flag}: exited {rc}: {err[:200]}")
                continue

            lines = [l for l in out.splitlines() if l.strip()]
            if flag in THEORY_FLAGS:
                idents, notes = [], {}
                for line in lines:
                    ident, note = split_theory_line(line)
                    idents.append(ident)
                    if note:
                        notes[ident] = note
                capabilities[key] = idents
                if notes:
                    partial_support[key] = notes
            else:
                # Not yet parsed into a strict shape — raw lines only,
                # until real output has been inspected.
                capabilities[key] = lines

        status = "ok" if not errors else "incomplete"
        record = {
            "id": solver_id, "version": version, "status": status,
            "reported_name": name, "reported_version": ver,
            "capabilities": capabilities,
        }
        if partial_support:
            record["partial_support"] = partial_support
        if errors:
            record["errors"] = errors

        print(json.dumps(record))
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
