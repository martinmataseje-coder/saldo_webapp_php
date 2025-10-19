# app_streamlit.py
import datetime as dt
from pathlib import Path
import streamlit as st

from saldo_core import generate_saldo_document  # musí existovať v saldo_core.py

st.set_page_config(page_title="Saldo generátor", page_icon="📄", layout="centered")
st.title("Saldo – generátor")

st.caption(
    "TEMPLATE a POMÔCKA sa načítajú automaticky z priečinka data/. "
    "Používateľ nahráva iba vstupy (pohyby a väzby). Logo je voliteľné."
)

# ---------- AUTO LOAD z data/ ----------
TEMPLATE_PATH = Path("data/TEMPLATE_saldo.XLSX")
HELPER_PATH   = Path("data/pomocka k saldo (vlookup).XLSX")

missing = []
if not TEMPLATE_PATH.exists(): missing.append(TEMPLATE_PATH.name)
if not HELPER_PATH.exists():   missing.append(HELPER_PATH.name)
if missing:
    st.error(
        "Chýbajú systémové súbory v priečinku data/: " + ", ".join(missing) +
        ". Nahraj ich do data/ a skús znova."
    )
    st.stop()

# Načítaj ich hneď do pamäte (aby sa dali použiť aj 2× pri 'Oboje')
t_bytes = TEMPLATE_PATH.read_bytes()
h_bytes = HELPER_PATH.read_bytes()

# ---------- Uploady / vstupy ----------
src1 = st.file_uploader("Vstupný súbor 1 (pohyby)", type=["xlsx"])
src2 = st.file_uploader("Vstupný súbor 2 (väzby)", type=["xlsx"])

colA, colB = st.columns(2)
with colA:
    hdr_meno = st.text_input("Meno zákazníka", value="Jožko Mrkvička")
    hdr_sap  = st.text_input("SAP ID", value="1090989")
with colB:
    hdr_ucet = st.text_input("Zmluvný účet", value="777777777")
    hdr_spol = st.text_input("Názov spoločnosti", value="SWAN a.s.")

col1, col2, col3 = st.columns(3)
with col1:
    export_choice = st.radio("Exportovať ako", ["XLSX", "PDF", "Oboje"], horizontal=True, index=0)
with col2:
    theme = st.selectbox("Téma výstupu", ["blue", "gray", "warm"], index=0)  # farba v XLS; PDF má 4ka tyrkys
with col3:
    # voliteľne si necháme aj textové pole (ak chceš natvrdo zadávať cestu); nebude to však rušiť
    logo_path = st.text_input("Cesta k logu (voliteľné)", value="data/logo_4ka_circle.png")

# ---------- Logo (upload alebo auto-detect v data/) ----------
logo_bytes = None
logo_upload = st.file_uploader("Logo (voliteľné)", type=["png", "jpg", "jpeg"])
if logo_upload:
    logo_bytes = logo_upload.read()
else:
    candidates = []
    if logo_path and logo_path.strip():
        candidates.append(logo_path.strip())
    candidates += [
        "data/logo_4ka_circle.png",
        "data/logo_4ka.png",
        "data/logo.png",
        "data/Logo_4ka.png",
        "data/LOGO_4KA.PNG",
    ]
    for cand in candidates:
        p = Path(cand)
        if p.exists() and p.is_file():
            try:
                logo_bytes = p.read_bytes()
                break
            except Exception:
                continue
# ak sa nenašlo, ticho pokračujeme bez loga

st.divider()

# ---------- Generovanie ----------
if st.button("Generovať", use_container_width=True):
    if not src1 or not src2:
        st.error("Nahraj oba vstupy: Vstup 1 (pohyby) a Vstup 2 (väzby).")
        st.stop()

    s1_bytes = src1.read()
    s2_bytes = src2.read()

    safe_name = (hdr_meno or "report").strip().replace(" ", "_")
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    xlsx_bytes = None
    pdf_bytes  = None

    # XLSX
    if export_choice in ("XLSX", "Oboje"):
        try:
            xlsx_bytes = generate_saldo_document(
                t_bytes, h_bytes, s1_bytes, s2_bytes,
                hdr_meno=hdr_meno, hdr_sap=hdr_sap, hdr_ucet=hdr_ucet, hdr_spol=hdr_spol or "SWAN a.s.",
                theme=theme, logo_bytes=logo_bytes, output="xlsx"
            )
            st.success("✅ XLSX vygenerovaný")
        except Exception as e:
            st.error(f"Chyba pri generovaní XLSX: {e}")
            st.stop()

    # PDF
    if export_choice in ("PDF", "Oboje"):
        try:
            pdf_bytes = generate_saldo_document(
                t_bytes, h_bytes, s1_bytes, s2_bytes,
                hdr_meno=hdr_meno, hdr_sap=hdr_sap, hdr_ucet=hdr_ucet, hdr_spol=hdr_spol or "SWAN a.s.",
                theme=theme, logo_bytes=logo_bytes, output="pdf"
            )
            st.success("✅ PDF vygenerované")
        except Exception as e:
            st.error(f"Chyba pri generovaní PDF: {e}")
            st.stop()

    st.write("### Stiahnuť výstupy")
    if xlsx_bytes is not None and export_choice in ("XLSX", "Oboje"):
        st.download_button(
            "⬇️ Stiahnuť XLSX",
            data=xlsx_bytes,
            file_name=f"{safe_name}_saldo_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    if pdf_bytes is not None and export_choice in ("PDF", "Oboje"):
        st.download_button(
            "⬇️ Stiahnuť PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}_saldo_{ts}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.caption("Dáta (vstupy) sa spracujú iba v pamäti a neukladajú sa na server.")
