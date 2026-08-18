---
name: Python runtime compatibility
description: The imported project declares Python 3.13 but the configured Replit runtime is Python 3.12.
---

Use the pinned packages in `backend/requirements.txt` inside a local `.venv` for backend checks and the dashboard workflow; do not broaden the runtime or migrate the project just to resolve the declaration mismatch.

**Why:** The imported workspace currently exposes Python 3.12, while the root project metadata requires Python 3.13; installing directly against the immutable system interpreter is not reliable.

**How to apply:** If backend packages are unavailable, create `.venv` with the configured Python and install `backend/requirements.txt`; keep the existing app stack unchanged.