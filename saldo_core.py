
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

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

def generate_saldo_xlsx(
    template_bytes: bytes,
    helper_bytes: bytes,
    src1_bytes: bytes,
    src2_bytes: bytes,
    hdr_meno: str,
    hdr_sap: str,
    hdr_ucet: str,
    hdr_spol: str = "SWAN a.s."
) -> bytes:
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

    wb_h = load_workbook(BytesIO(helper_bytes), data_only=True)
    ws_h = wb_h[wb_h.sheetnames[0]]
    hdr_h = [ws_h.cell(row=1, column=c).value for c in range(1, ws_h.max_column+1)]
    def idx_h(name):
        for i,h in enumerate(hdr_h, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    h_src = idx_h("Označenie pôvodu")
    h_dst = idx_h("Typ dokladu")
    if not h_src or not h_dst:
        raise RuntimeError("V pomôcke chýba 'Označenie pôvodu' alebo 'Typ dokladu'.")

    pom_map = {}
    for r in range(2, ws_h.max_row+1):
        s = ws_h.cell(row=r, column=h_src).value
        t = ws_h.cell(row=r, column=h_dst).value
        if isinstance(s,str) and s.strip()!="":
            pom_map[s.strip()] = t.strip() if isinstance(t,str) else t

    wb1 = load_workbook(BytesIO(src1_bytes), data_only=True)
    ws1 = wb1[wb1.sheetnames[0]]
    hdr1 = [ws1.cell(row=1, column=c).value for c in range(1, ws1.max_column+1)]
    def idx1(name):
        for i,h in enumerate(hdr1, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    i_doc = idx1("Číslo dokladu")
    i_dz  = idx1("Dátum zadania")
    i_du  = idx1("Dátum účtovania")
    i_sn  = idx1("Splatnosť netto")
    i_op  = idx1("Označenie pôvodu")
    i_amt = idx1("Čiastka")

    if ws.max_row>HEADER_ROW:
        ws.delete_rows(HEADER_ROW+1, ws.max_row-HEADER_ROW)

    r0 = HEADER_ROW+1
    for r in range(2, ws1.max_row+1):
        row_has_data = any(ws1.cell(row=r, column=c).value not in (None,"") for c in range(1, ws1.max_column+1))
        if not row_has_data:
            continue
        ozn_pov = ws1.cell(row=r, column=i_op).value if i_op else None
        mapped_typ = pom_map.get(ozn_pov.strip() if isinstance(ozn_pov, str) else ozn_pov, None)
        ws.cell(row=r0, column=c_doc, value=ws1.cell(row=r, column=i_doc).value if i_doc else None)
        ws.cell(row=r0, column=c_dz,  value=ws1.cell(row=r, column=i_dz).value if i_dz else None)
        ws.cell(row=r0, column=c_du,  value=ws1.cell(row=r, column=i_du).value if i_du else None)
        ws.cell(row=r0, column=c_sn,  value=ws1.cell(row=r, column=i_sn).value if i_sn else None)
        ws.cell(row=r0, column=c_typ, value=mapped_typ if mapped_typ is not None else None)
        ws.cell(row=r0, column=c_amt, value=ws1.cell(row=r, column=i_amt).value if i_amt else None)
        r0 += 1

    L_G = get_column_letter(c_amt); L_H = get_column_letter(c_bal)
    last = _last_data_row(ws, c_doc)
    for r in range(HEADER_ROW+1, last+1):
        ws.cell(row=r, column=c_bal, value=f"={L_G}{r}" if r==HEADER_ROW+1 else f"={L_H}{r-1}+{L_G}{r}")
    for c in (c_dz, c_du, c_sn):
        if c:
            for r in range(HEADER_ROW+1, last+1):
                ws.cell(row=r, column=c).number_format = DATE_FMT

    wb2 = load_workbook(BytesIO(src2_bytes), data_only=True)
    ws2 = wb2[wb2.sheetnames[0]]
    hdr2 = [ws2.cell(row=1, column=c).value for c in range(1, ws2.max_column+1)]
    def idx2(name):
        for i,h in enumerate(hdr2, start=1):
            if isinstance(h,str) and h.strip()==name:
                return i
        return None
    j_doc = idx2("Číslo dokladu")
    j_ref = idx2("Doplnková referencia")
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
                if s.upper().startswith("VBRK"):
                    s = s[4:].strip()
            elif v is not None:
                s = str(v)
            ref_map[str(k).strip()] = s

    def is_faktura(v): return isinstance(v, str) and v.strip()=="Faktúra"
    for r in range(HEADER_ROW+1, last+1):
        doc = ws.cell(row=r, column=c_doc).value
        typ = ws.cell(row=r, column=c_typ).value
        if is_faktura(typ):
            inv = ref_map.get(str(doc).strip() if doc not in (None,"") else "", "")
            ws.cell(row=r, column=c_inv, value=inv if inv else None)
        else:
            ws.cell(row=r, column=c_inv, value=None)

    ws["B1"] = hdr_sap
    ws["B2"] = hdr_meno
    ws["B3"] = hdr_spol
    ws["B4"] = hdr_ucet
  
    # === [NOVÝ KROK] Výpočet a zápis celkového zostatku ===
    try:
        last_data_row = ws.max_row
        zostatok_col = None
        for cell in ws[1]:
            if str(cell.value).strip().lower() == "zostatok":
                zostatok_col = cell.column_letter
                break
        if zostatok_col:
            summary_row = last_data_row + 2
            ws[f"{zostatok_col}{summary_row-1}"] = ""
            ws[f"{zostatok_col}{summary_row}"] = f"=SUM({zostatok_col}2:{zostatok_col}{last_data_row})"
            ws[f"{zostatok_col}{summary_row}"].number_format = '#,##0.00 [$€-407]'
            ws[f"{zostatok_col}{summary_row}"].font = Font(bold=True)
            prev_col = chr(ord(zostatok_col) - 1)
            ws[f"{prev_col}{summary_row}"] = "Celkový zostatok:"
            ws[f"{prev_col}{summary_row}"].font = Font(bold=True)
    except Exception as e:
        print(f"Chyba pri výpočte celkového zostatku: {e}")
    # === [KONIEC NOVÉHO KROKU] ===

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()
