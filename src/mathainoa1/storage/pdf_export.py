"""PDF-Export von Wortlisten als Tabelle (fpdf2).

Die PDF-Standardschriften können kein Griechisch — deshalb liegt
DejaVuSans.ttf in assets/fonts und wird hier eingebettet.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from fpdf import FPDF
    from fpdf.fonts import FontFace
except ImportError:  # Paket fehlt (z.B. abgespeckte Test-Umgebung)
    FPDF = None
    FontFace = None


def _font_path() -> Path | None:
    """DejaVuSans.ttf: Assets der gepackten App oder Repo-Ordner."""
    assets = os.environ.get("FLET_ASSETS_DIR")
    candidates = []
    if assets:
        candidates.append(Path(assets) / "fonts" / "DejaVuSans.ttf")
    candidates.append(Path(__file__).resolve().parents[3]
                      / "assets" / "fonts" / "DejaVuSans.ttf")
    for p in candidates:
        if p.exists():
            return p
    return None


def export_pdf(title: str, header: list[str],
               rows: list[list[str]]) -> bytes:
    """Tabellen-PDF (Querformat ab 6 Spalten). RuntimeError, wenn fpdf2
    oder die mitgelieferte Schrift fehlt."""
    if FPDF is None:
        raise RuntimeError("PDF-Export nicht verfügbar (fpdf2 fehlt).")
    font = _font_path()
    if font is None:
        raise RuntimeError("Schrift assets/fonts/DejaVuSans.ttf fehlt.")
    pdf = FPDF(orientation="L" if len(header) > 5 else "P", format="A4")
    pdf.set_margin(12)
    pdf.set_auto_page_break(True, margin=12)
    pdf.add_font("dejavu", "", str(font))
    pdf.add_page()
    pdf.set_font("dejavu", size=14)
    pdf.cell(0, 8, title)
    pdf.ln(12)
    pdf.set_font("dejavu", size=9)
    # Kopfzeile ohne Fettdruck (nur die normale Schrift ist eingebettet),
    # stattdessen grau hinterlegt
    heading = FontFace(fill_color=(225, 228, 235))
    with pdf.table(first_row_as_headings=True,
                   headings_style=heading, line_height=5.5,
                   padding=1.5) as table:
        row = table.row()
        for h in header:
            row.cell(h)
        for values in rows:
            row = table.row()
            for v in values:
                row.cell(v or "")
    return bytes(pdf.output())
