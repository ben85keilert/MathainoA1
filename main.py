import sys
from pathlib import Path

# In der gepackten App (flet build) ist mathainoa1 nicht pip-installiert,
# sondern liegt als Quellbaum unter src/ neben dieser Datei.
sys.path.insert(0, str(Path(__file__).parent / "src"))

import flet as ft

from mathainoa1.ui.app import main

ft.run(main)