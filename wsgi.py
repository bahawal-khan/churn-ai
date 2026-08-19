"""PythonAnywhere WSGI entry point (`PHASE_12_DEPLOYMENT.md` §2).

PythonAnywhere's Web tab auto-generates its own WSGI config file at
`/var/www/<username>_pythonanywhere_com_wsgi.py`. That file is edited
directly on PythonAnywhere (an account action, not version-controlled) and
must be replaced with:

    import sys

    path = "/home/<username>/churn-ai"  # repo root on PythonAnywhere
    if path not in sys.path:
        sys.path.insert(0, path)

    from wsgi import application

This keeps the actual app-loading logic here, in git, instead of duplicated
inside PythonAnywhere's own generated file. Uses the existing Flask
application factory (`backend.app.create_app`) unchanged — no new
configuration objects or app-construction logic introduced here.
"""

from __future__ import annotations

from backend.app import create_app

application = create_app()
