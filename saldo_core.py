# saldo_core.py
from io import BytesIO
from typing import Literal, Optional
import datetime as _dt

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage

# PDF export
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HEADER_ROW = 9
DATE_FMT   = "DD.MM.YY"

# ---------- helpers (xlsx) ----------
def _find_col(headers, name):
    for i, h in enumerate(headers, start=1):
        if isinstance(h, str) and h.strip() == name:
            return i
    return None

def _last_data_row(ws, key_col):
    last = HEADER_ROW
    for r in range(HEADER_ROW+1, ws.max_row+1):
        if ws.cell(row=r, column=key_col).value not in (None, ""):
            last = r
    return last

# ---------- helpers (PDF) ----------
def _register_fonts():
    """Registruje DejaVu Sans (ak je v data/), inak padá na Helvetica."""
    try:
        import os
        base = os.path.dirname(__file__)
        ttf_regular = os.path.join(base, "data", "DejaVuSans.ttf")
        ttf_bold    = os.path.join(base, "data", "DejaVuSans-Bold.ttf")
        if os.path.exists(ttf_regular) and os.path.exists(ttf_bold):
            pdfmetrics.registerFont(TTFont("DejaVuSans", ttf_regular))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", ttf_bold))
            return ("DejaVuSans", "DejaVuSans-Bold")
    except Exception:
        pass
    return ("Helvetica", "Helvetica-Bold")

def _fmt_date(v):
    import datetime
    if isinstance(v, (datetime.datetime, _dt.datetime, datetime.date, _dt.date)):
        return v.strftime("%d.%m.%Y")
    s = str(v).strip() if v is not None else ""
    if " " in s: s = s.split(" ")[0]
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 3 and all(parts):
            yyyy, mm, dd = parts
            return f"{dd}.{mm}.{yyyy}"
    return s

def _num(v):
    try:
        return float(v)
    except Exception:
        return None

def _fmt_money(x):
    if x is None:
        return ""
    s = f"{x:,.2f}".replace(",", " ")
    return s + "\u00A0€"

# Palety tém
THEMES = {
    "blue": {
        "header_hex": "#25B3AD",
        "alt_row": "#F9FEFD",
        "grid": "#E2E8F0",
    },
    "gray": {
        "header_hex": "#4A5568",
        "alt_row": "#F7F7F7",
        "grid": "#D9D9D9",
    },
    "warm": {
        "header_hex": "#C6A875",
        "alt_row": "#FFF9F2",
        "grid": "#EADDC8",
    },
}

def _build_pdf(ws, hdr_meno, hdr_sap, hdr_ucet, hdr_spol, logo_bytes: Optional[bytes], theme="blue"):
    FONT_REG, FONT_BOLD = _register_fonts()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="HdrTitle", parent=styles["Title"], fontName=FONT_BOLD, alignment=0))
    styles.add(ParagraphStyle(name="Base", parent=styles["Normal"], fontName=FONT_REG, fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="HdrSmall", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9, alignment=1))
    styles.add(ParagraphStyle(name="Cell", parent=styles["Normal"], fontName=FONT_REG, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CellRight", parent=styles["Normal"], fontName=FONT_REG, fontSize=8, leading=10, alignment=2))

    # Téma farieb
    th = THEMES.get(theme, THEMES["blue"])

    # pôvodné hlavičky
    xhdrs = [ws.cell(row=HEADER_ROW, column=c).value for c in range(1, ws.max_column+1)]
    c_doc = _find_col(xhdrs, "Číslo dokladu")
    c_inv = _find_col(xhdrs, "číslo Faktúry") or _find_col(xhdrs, "Číslo Faktúry")
    c_dz  = _find_col(xhdrs, "Dátum zadania")
    c_du  = _find_col(xhdrs, "Dátum účtovania")
    c_sn  = _find_col(xhdrs, "Splatnosť netto")
    c_typ = _find_col(xhdrs, "Typ dokladu")
    c_amt = _find_col(xhdrs, "Čiastka")
    c_bal = _find_col(xhdrs, "Zostatok")
    last  = _last_data_row(ws, c_doc)

    pdf_hdrs = ["Č. dokladu", "Č. faktúry", "Dátum zadania", "Dátum účt.", "Splatnosť",
                "Typ dokladu", "Čiastka", "Zostatok"]

    data = [[Paragraph(h, styles["HdrSmall"]) for h in pdf_hdrs]]
    run_bal = 0.0
    def _is_faktura(txt): return isinstance(txt, str) and txt.strip().lower() == "faktúra"

    for r in range(HEADER_ROW+1, last+1):
        doc = ws.cell(row=r, column=c_doc).value
        inv = ws.cell(row=r, column=c_inv).value
        dz  = ws.cell(row=r, column=c_dz).value
        du  = ws.cell(row=r, column=c_du).value
        sn  = ws.cell(row=r, column=c_sn).value
        typ = ws.cell(row=r, column=c_typ).value
        amt = _num(ws.cell(row=r, column=c_amt).value)
        add_amt = amt if amt is not None else 0.0
        run_bal += add_amt

        row = [
            Paragraph("" if doc is None else str(doc), styles["Cell"]),
            Paragraph("" if (inv is None or not _is_faktura(typ)) else str(inv), styles["Cell"]),
            Paragraph(_fmt_date(dz), styles["Cell"]),
            Paragraph(_fmt_date(du), styles["Cell"]),
            Paragraph(_fmt_date(sn), styles["Cell"]),
            Paragraph("" if typ is None else str(typ), styles["Cell"]),
            Paragraph(_fmt_money(amt), styles["CellRight"]),
            Paragraph(_fmt_money(run_bal), styles["CellRight"]),
        ]
        data.append(row)

    # len zostatok, bold, rovnaká farba ako header
    total_row = [Paragraph("", styles["Cell"]) for _ in range(8)]
    total_row[5] = Paragraph("<b>Súčet</b>", styles["HdrSmall"])
    total_row[7] = Paragraph(f"<b>{_fmt_money(run_bal)}</b>", styles["CellRight"])
    data.append(total_row)

    # Layout
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)

    # Hlavička s logom vľavo, text vpravo
    title = Paragraph("Náhľad na fakturačný účet – saldo", styles["HdrTitle"])
    date_p = Paragraph(f"Dátum generovania: {_dt.datetime.now().strftime('%d.%m.%Y')}", styles["Base"])
    meta = Paragraph(
        f"{hdr_spol} — <font name='{FONT_BOLD}'>Meno:</font> {hdr_meno} • "
        f"<font name='{FONT_BOLD}'>SAP ID:</font> {hdr_sap} • "
        f"<font name='{FONT_BOLD}'>Zmluvný účet:</font> {hdr_ucet}",
        styles["Base"]
    )

    header_tbl_data = []
    if logo_bytes:
        rlimg = RLImage(BytesIO(logo_bytes), width=60, height=60)
        header_tbl_data.append([rlimg, Spacer(10, 10), [title, date_p, meta]])
        col_head_widths = [60, 10, None]
    else:
        header_tbl_data.append(["", "", [title, date_p, meta]])
        col_head_widths = [0, 0, None]

    header_tbl = Table(header_tbl_data, colWidths=col_head_widths, hAlign="LEFT")
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))

    story = [header_tbl, Spacer(1, 6)]

    # tabuľka
    col_widths = [75, 60, 58, 58, 58, 70, 62, 68]
    table = Table(data, repeatRows=1, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(th["header_hex"])),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor(th["grid"])),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor(th["alt_row"])]),
        ("ALIGN", (2,1), (4,-2), "CENTER"),
        ("ALIGN", (6,1), (7,-2), "RIGHT"),
        ("ALIGN", (7,-1), (7,-1), "RIGHT"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("FONTSIZE", (0,1), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING",(0,0), (-1,-1), 2),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor(th["header_hex"])),
        ("TEXTCOLOR",  (0,-1), (-1,-1), colors.white),
        ("FONTNAME",   (5,-1), (5,-1), FONT_BOLD),
        ("FONTNAME",   (7,-1), (7,-1), FONT_BOLD),
    ]))

    story.append(table)
    doc.build(story)
    buf.seek(0)
    return buf.read()
