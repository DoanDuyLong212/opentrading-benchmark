"""Import bootstrap for every v4.7 test file, including standalone invocations."""
from pathlib import Path
import sys
TOOLS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS/'runners')]

