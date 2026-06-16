"""Pytest fixtures: isolate each test run on a fresh temp SQLite database.

DATA_DIR is set before the app package imports config so the DB lives under a
throwaway directory.
"""
import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="scout-test-"))
os.environ.setdefault("STATIC_DIR", tempfile.mkdtemp(prefix="scout-static-"))
