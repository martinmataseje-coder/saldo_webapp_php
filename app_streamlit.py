# app_streamlit.py
import os
import datetime as dt
import streamlit as st

DEFAULT_LOGO_PATH = "data/logo_4ka_circle.png"
TEMPLATE_PATH     = "data/TEMPLATE_saldo.XLSX"
HELPER_PATH       = "data/pomocka k saldo (vlookup).XLSX"

def load_file_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

st.set_page_config(page_title="Saldo generátor", page_icon="📄", layout="centered")
st.title("Saldo – generátor")

# bezpečný import core, aby sa chyba ukázala priamo v UI
try:
    from saldo_core import generate_saldo_document
except Exception as e:
    st.error("Nepodarilo sa načítať modul `saldo_core.py`.")
    st.exception(e)
    st.stop()

# --- UI vstupy ---
with st.container():
    colA, colB = st.columns(2)
    with colA:
        src1 = st.file_uploader("Vstup 1 (pohyby)", type=["xlsx"])
    with colB:
        src2 = st.file_uploader("Vstup 2 (väzby)", type=["xlsx"])

st.caption("Template a Pomôcka sa načítajú automaticky z priečinka `data/`.")

st.divider()

col1, col2 = st.columns(2)
with col1:
    hdr_meno = st.text_input("Meno zákazníka", "Jožko Mrkvička")
    hdr_sap  = st.text_input("SAP ID", "1090989")
with col2:
    hdr_ucet = st.text_input("Zmluvný účet", "777777777")
    hdr_spol = st.text_input("Názov spoločnosti", "SWAN a.s.")

export_choice = st.radio("Exportovať ako", ["XLS", "PDF", "Oboje"], horizontal=True)

# firemná schéma
theme = "blue"

st.divider()

if st.button("Generovať", use_container_width=True):
    try:
        # kontrola vstupov (iba 2 vstupy od užívateľa)
        if not all([src1, src2]):
            st.error("Nahraj oba vstupy: 'Vstup 1 (pohyby)' a 'Vstup 2 (väzby)'.")
            st.stop()

        # načítaj fixné súbory z data/
        template_bytes = load_file_bytes(TEMPLATE_PATH)
        helper_bytes   = load_file_bytes(HELPER_PATH)
        if not template_bytes:
            st.error(f"Chýba template: `{TEMPLATE_PATH}`")
            st.stop()
        if not helper_bytes:
            st.error(f"Chýba pomôcka: `{HELPER_PATH}`")
            st.stop()

        # načítaj logo (pevné)
        logo_bytes = load_file_bytes(DEFAULT_LOGO_PATH)
        if not logo_bytes:
            st.warning(f"Logo sa nepodarilo načítať z '{DEFAULT_LOGO_PATH}'. PDF sa vytvorí bez loga.")

        # bytes z uploadov
        src1_bytes = src1.read()
        src2_bytes = src2.read()

        # vygeneruj XLS
        xls_bytes = generate_saldo_document(
            template_bytes, helper_bytes, src1_bytes, src2_bytes,
            hdr_meno=hdr_meno, hdr_sap=hdr_sap, hdr_ucet=hdr_ucet, hdr_spol=hdr_spol,
            theme=theme, logo_bytes=logo_bytes, output="xlsx"
        )

        safe_name = (hdr_meno or "report").strip().replace(" ", "_")
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = "data"
        os.makedirs(out_dir, exist_ok=True)
        xls_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.xlsx")
        with open(xls_path, "wb") as f:
            f.write(xls_bytes)

        st.success(f"✅ XLS vygenerovaný: {xls_path}")
        st.download_button(
            "⬇️ Stiahnuť XLS",
            data=xls_bytes,
            file_name=os.path.basename(xls_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # vygeneruj PDF ak treba
        if export_choice in ("PDF", "Oboje"):
            pdf_bytes = generate_saldo_document(
                template_bytes, helper_bytes, src1_bytes, src2_bytes,
                hdr_meno=hdr_meno, hdr_sap=hdr_sap, hdr_ucet=hdr_ucet, hdr_spol=hdr_spol,
                theme=theme, logo_bytes=logo_bytes, output="pdf"
            )
            pdf_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            st.success(f"✅ PDF vygenerované: {pdf_path}")
            st.download_button(
                "⬇️ Stiahnuť PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True
            )

    except Exception as e:
        st.error("Pri generovaní nastala chyba.")
        st.exception(e)
