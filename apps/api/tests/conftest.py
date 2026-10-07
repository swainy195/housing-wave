"""Keep ordinary API tests on the deterministic JSON repository."""

import os


os.environ.setdefault("DATABASE_MODE", "json")
