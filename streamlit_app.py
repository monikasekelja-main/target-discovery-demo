"""Streamlit entry point; execute the UI afresh on every Streamlit rerun."""
from runpy import run_module

run_module("target_discovery.ui.app", run_name="__main__")
