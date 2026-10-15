#!/usr/bin/env python
"""Dump the FastAPI OpenAPI schema to openapi.json.

Usage (from repo root):
    python scripts/generate_openapi.py

Requires the API dependencies to be installed. Imports are isolated so that a
missing optional dependency surfaces a clear error rather than a traceback into
the whole app.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api" / "python"
OUT = ROOT / "openapi.json"


def main() -> int:
    sys.path.insert(0, str(API_DIR))
    try:
        from main import app
    except Exception as e:  # pragma: no cover - environment dependent
        print(f"ERROR: could not import FastAPI app: {type(e).__name__}: {e}", file=sys.stderr)
        print("Install API deps first: pip install -r api/python/requirements.txt", file=sys.stderr)
        return 1

    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(json.dumps(schema))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
