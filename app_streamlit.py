# app_streamlit.py
import datetime as dt
from pathlib import Path
import streamlit as st

from saldo_core import generate_saldo_document  # <- dôležité: táto funkcia MUSÍ existovať v saldo_core.py

st.set_page_config(page_title="Saldo generátor", page_icon="📄", layout="centered")
st.title("Saldo – generátor")

st.caption("Nahraj TEMPLATE, POMÔCKU a dva vstupy. Logo je voliteľné cez cestu k súboru.")

# ---- Uploady / vstupy ----
template = st.file_uploader("TEMPLATE_saldo.xlsx", type=["xlsx"])
helper   = st.file_uploader("pomocka_saldo.xlsx", type=["xlsx"])
src1     = st.file_uploader("Vstupný súbor 1 (pohyby)", type=["xlsx"])
src2     = st.file_uploader("Vstupný súbor 2 (väzby)", type=["xlsx"])

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
    theme = st.selectbox("Téma výstupu", ["blue", "gray", "warm"], index=0)
with col3:
    logo_path = st.text_input("Cesta k logu (voliteľné)", value="data/logo_4ka_circle.png")

st.divider()

if st.button("Generovať", use_container_width=True):
    # Kontroly vstupov
    missing = []
    if not template: missing.append("TEMPLATE")
    if not helper:   missing.append("POMÔCKA")
    if not src1:     missing.append("Vstup 1 (pohyby)")
    if not src2:     missing.append("Vstup 2 (väzby)")
    if missing:
        st.error("Chýbajú súbory: " + ", ".join(missing))
        st.stop()

    # Načítaj všetky uploady do pamäte (aby sa dali použiť viackrát)
    t_bytes = template.read()
    h_bytes = helper.read()
    s1_bytes = src1.read()
    s2_bytes = src2.read()

    # Logo bytes (voliteľné)
    logo_bytes = None
    lp = Path(logo_path) if logo_path else None
    if lp and lp.exists() and lp.is_file():
        try:
            logo_bytes = lp.read_bytes()
        except Exception as e:
            st.warning(f"Logo sa nepodarilo načítať ({e}). Pokračujem bez loga.")
    elif logo_path:
        st.info("Logo sa nenašlo na zadanej ceste. Pokračujem bez loga.")

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

    st.caption("Dáta sa spracujú iba v pamäti a neukladajú sa na server.")
