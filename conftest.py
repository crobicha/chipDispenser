import sys
from pathlib import Path

# Ensure the project root is on sys.path so `hardware` package is importable
# regardless of pytest version (pythonpath= in pytest.ini requires pytest >= 7.0)
sys.path.insert(0, str(Path(__file__).parent))
