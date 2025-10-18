# saldo_core.py
from io import BytesIO
from typing import Literal, Optional
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage

# PDF export (vyžaduje reportlab v requirements.txt)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

HEADER_ROW = 9
DATE_FMT   = "DD.MM.YY"

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

def _style_ws(ws, c_doc, c_inv, c_dz, c_du, c_sn, c_typ, c_amt, c_bal, last, theme="blue"):
    # farby témy (light header + zebra)
    if theme == "blue":
        header_fill = PatternFill("solid", fgColor="EAF2FE")
        zebra_fill  = PatternFill("solid", fgColor="F7FAFF")
        head_font   = Font(bold=True, color="0F172A")
    elif theme == "gray":
        header_fill = PatternFill("solid", fgColor="EEEEEE")
        zebra_fill  = PatternFill("solid", fgColor="F7F7F7")
        head_font   = Font(bold=True, color="111111")
    else:
        # warm
        header_fill = PatternFill("solid", fgColor="FFF7E6")
        zebra_fill  = PatternFill("solid", fgColor="FFFBF2")
        head_font   = Font(bold=True, color="111111")

    thin = Side(style="thin", color="D0D7E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # hlavička
    for c in range(1, ws.max_column+1):
        cell = ws.cell(row=HEADER_ROW, column=c)
        cell.font = head_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = border

    # šírky
    widths = {c_doc:16, c_inv:18, c_dz:14, c_du:16, c_sn:16, c_typ:22, c_amt:14, c_bal:14}
    for col_idx, w in widths.items():
        if col_idx:
            ws.column_dimensions[get_column_letter(col_idx)].width = w

    # formát čísel
    for r in range(HEADER_ROW+1, last+1):
        if c_amt: ws.cell(row=r, column=c_amt).number_format = '#,##0.00'
        if c_bal: ws.cell(row=r, column=c_bal).number_format = '#,##0.00'

    # zebra + orámovanie
    for r in range(HEADER_ROW+1, last+1):
        if (r - (HEADER_ROW+1)) % 2 == 0:
            for c in range(1, ws.max_column+1):
                ws.cell(row=r, column=c).fill = zebra_fill
                ws.cell(row=r, column=c).border = border

def _insert_logo(ws, logo_bytes: Optional[bytes]):
    if not logo_bytes:
        return
    try:
        bio = BytesIO(logo_bytes)
        img = XLImage(bio)
        ws.add_image(img, "A1")
    except Exception:
        pass

def _build_pdf(ws, hdr_meno, hdr_sap, hdr_ucet, hdr_spol, header_hex="#EAF2FE"):
    headers = [ws.cell(row=HEADER_ROW, column=c).value for c in range(1, ws.max_column+1)]
    c_doc = _find_col(headers, "Číslo dokladu")
    last = _last_data_row(ws, c_doc)
    data = [headers]
    for r in range(HEADER_ROW+1, last+1):
        data.append([ws.cell(row=r, column=c).value for c in range(1, ws.max_column+1)])

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("<b>Náhľad na fakturačný účet – saldo</b>", styles["Title"])
    meta  = Paragraph(f"{hdr_spol} — Meno: <b>{hdr_meno}</b> • SAP ID: <b>{hdr_sap}</b> • Zmluvný účet: <b>{hdr_ucet}</b>", styles["Normal"])
    story += [title, Spacer(1, 6), meta, Spacer(1, 12)]

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(header_hex)),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#0F172A")),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D0D7E1")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFF")]),
        ("FONTSIZE", (0,1), (-1,-1), 8),
    ]))
    story.append(table)
    doc.build(story)
    buf.seek(0)
    return buf.read()

def generate_saldo_document(
    template_bytes: bytes,
    helper_bytes: bytes,
    src1_bytes: bytes,
    src2_bytes: bytes,
    hdr_meno: str,
    hdr_sap: str,
    hdr_ucet: str,
    hdr_spol: str = "SWAN a.s.",
    theme: Literal["blue","gray","warm"] = "blue",
    logo_bytes: Optional[bytes] = None,
    output: Literal["xlsx","pdf"] = "xlsx",
) -> bytes:

    # --- TEMPLATE ---
    wb = load_workbook(BytesIO(template_bytes), data_only=False)
    ws = wb[wb.sheetnames[0]]
    headers = [ws.cell(row=HEADER_ROW, column=c).value for c in range(1, ws.max_column+1)]
    c_doc = _find_col(headers, "Číslo dokladu")
    c_inv = _find_col(headers, "číslo Faktúry") or _find_col(headers, "Číslo Faktúry")
    c_dz  = _find_col(headers, "Dátum zadania")
    c_du  = _find_col(headers, "Dátum účtovania")
    c_sn  = _find_col(headers, "Splatnosť netto")
    c_typ = _find_col(headers, "Typ dokladu")
    c_amt = _find_col(headers, "Čiastka")
    c_bal = _find_col(headers, "Zostatok")
    if None in (c_doc, c_inv, c_dz, c_du, c_sn, c_typ, c_amt, c_bal):
        raise RuntimeError("V TEMPLATE chýba niektorý povinný stĺpec.")

    # --- HELPER ---
    wb_h = load_workbook(BytesIO(helper_bytes), data_only=True); ws_h = wb_h[wb_h.sheetnames[0]]
    hdr_h = [ws_h.cell(row=1, column=c).value for c in range(1, ws_h.max_column+1)]
    def idx_h(name):
        for i,h in enumerate(hdr_h, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    h_src = idx_h("Označenie pôvodu"); h_dst = idx_h("Typ dokladu")
    if not h_src or not h_dst:
        raise RuntimeError("V pomôcke chýba 'Označenie pôvodu' alebo 'Typ dokladu'.")
    pom_map = {}
    for r in range(2, ws_h.max_row+1):
        s = ws_h.cell(row=r, column=h_src).value
        t = ws_h.cell(row=r, column=h_dst).value
        if isinstance(s,str) and s.strip()!="":
            pom_map[s.strip()] = t.strip() if isinstance(t,str) else t

    # --- SRC1 (pohyby) + mapovanie typu ---
    wb1 = load_workbook(BytesIO(src1_bytes), data_only=True); ws1 = wb1[wb1.sheetnames[0]]
    hdr1 = [ws1.cell(row=1, column=c).value for c in range(1, ws1.max_column+1)]
    def idx1(name):
        for i,h in enumerate(hdr1, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    i_doc = idx1("Číslo dokladu"); i_dz=idx1("Dátum zadania"); i_du=idx1("Dátum účtovania")
    i_sn  = idx1("Splatnosť netto"); i_op=idx1("Označenie pôvodu"); i_amt=idx1("Čiastka")

    if ws.max_row>HEADER_ROW: ws.delete_rows(HEADER_ROW+1, ws.max_row-HEADER_ROW)

    r0 = HEADER_ROW+1
    for r in range(2, ws1.max_row+1):
        row_has_data = any(ws1.cell(row=r, column=c).value not in (None,"") for c in range(1, ws1.max_column+1))
        if not row_has_data: continue
        ozn_pov = ws1.cell(row=r, column=i_op).value if i_op else None
        mapped_typ = pom_map.get(ozn_pov.strip() if isinstance(ozn_pov, str) else ozn_pov, None)
        ws.cell(row=r0, column=c_doc, value=ws1.cell(row=r, column=i_doc).value if i_doc else None)
        ws.cell(row=r0, column=c_dz,  value=ws1.cell(row=r, column=i_dz).value if i_dz else None)
        ws.cell(row=r0, column=c_du,  value=ws1.cell(row=r, column=i_du).value if i_du else None)
        ws.cell(row=r0, column=c_sn,  value=ws1.cell(row=r, column=i_sn).value if i_sn else None)
        ws.cell(row=r0, column=c_typ, value=mapped_typ if mapped_typ is not None else None)
        ws.cell(row=r0, column=c_amt, value=ws1.cell(row=r, column=i_amt).value if i_amt else None)
        r0 += 1

    # --- Zostatok + dátumy ---
    L_G = get_column_letter(c_amt); L_H = get_column_letter(c_bal)
    last = _last_data_row(ws, c_doc)
    for r in range(HEADER_ROW+1, last+1):
        ws.cell(row=r, column=c_bal, value=f"={L_G}{r}" if r==HEADER_ROW+1 else f"={L_H}{r-1}+{L_G}{r}")
    for c in (c_dz, c_du, c_sn):
        if c:
            for rr in range(HEADER_ROW+1, last+1):
                ws.cell(row=rr, column=c).number_format = DATE_FMT

    # --- SRC2 (väzby) – Číslo Faktúry ---
    wb2 = load_workbook(BytesIO(src2_bytes), data_only=True); ws2 = wb2[wb2.sheetnames[0]]
    hdr2 = [ws2.cell(row=1, column=c).value for c in range(1, ws2.max_column+1)]
    def idx2(name):
        for i,h in enumerate(hdr2, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    j_doc = idx2("Číslo dokladu"); j_ref = idx2("Doplnková referencia")
    if not j_doc or not j_ref:
        raise RuntimeError("V zdroji 2 chýba 'Číslo dokladu' alebo 'Doplnková referencia'.")

    ref_map = {}
    for r in range(2, ws2.max_row+1):
        k = ws2.cell(row=r, column=j_doc).value
        v = ws2.cell(row=r, column=j_ref).value
        if k not in (None,""):
            s = ""
            if isinstance(v, str):
                s = v.strip()
                if s.upper().startswith("VBRK"): s = s[4:].strip()
            elif v is not None:
                s = str(v)
            ref_map[str(k).strip()] = s

    def is_faktura(v): return isinstance(v, str) and v.strip()=="Faktúra"
    for rr in range(HEADER_ROW+1, last+1):
        doc = ws.cell(row=rr, column=c_doc).value
        typ = ws.cell(row=rr, column=c_typ).value
        if is_faktura(typ):
            inv = ref_map.get(str(doc).strip() if doc not in (None,"") else "", "")
            ws.cell(row=rr, column=c_inv, value=inv if inv else None)
        else:
            ws.cell(row=rr, column=c_inv, value=None)

    # --- horná hlavička + logo + štýl
    ws["B1"] = hdr_sap; ws["B2"] = hdr_meno; ws["B3"] = hdr_spol; ws["B4"] = hdr_ucet
    _insert_logo(ws, logo_bytes)
    _style_ws(ws, c_doc, c_inv, c_dz, c_du, c_sn, c_typ, c_amt, c_bal, last, theme=theme)

    # --- export
    if output == "pdf":
        # farbu hlavičky tabuľky odvodíme z témy
        header_hex = {"blue":"#EAF2FE", "gray":"#EEEEEE", "warm":"#FFF7E6"}.get(theme, "#EAF2FE")
        return _build_pdf(ws, hdr_meno, hdr_sap, hdr_ucet, hdr_spol, header_hex=header_hex)

    out = BytesIO(); wb.save(out); out.seek(0); return out.read()
