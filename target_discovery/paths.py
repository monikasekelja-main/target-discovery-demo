"""Shared asset root for the source-checkout distribution.

Run the app from a complete checkout; fixtures and saved cases live alongside
this package. Resolve paths from this file rather than the working directory.
"""
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
