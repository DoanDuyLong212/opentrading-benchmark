"""Immutable archived tasks shared with v4.6u; audit assertions remain active."""
from pathlib import Path
LEGACY_STUDY = Path(__file__).resolve().parents[3]/'finance-v46-update-study'
RETIRED = LEGACY_STUDY/'tasks-retired'
