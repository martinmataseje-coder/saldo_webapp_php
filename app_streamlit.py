# app_streamlit.py
import io
import os
import datetime as dt
import streamlit as st

DEFAULT_LOGO_PATH = "data/logo_4ka_circle.png"

def load_logo_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

st.set_page_config(page_title="Saldo generátor", page_icon="📄", layout="centered")
st.title("Saldo – generátor")

# --- bezpečný import core, aby sa chyba ukázala priamo v UI ---
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
        template = st.file_uploader("TEMPLATE_saldo.xlsx", type=["xlsx"])
        helper   = st.file_uploader("pomôcka (vlookup).xlsx", type=["xlsx"])
    with colB:
        src1     = st.file_uploader("Vstup 1 (pohyby)", type=["xlsx"])
        src2     = st.file_uploader("Vstup 2 (väzby)", type=["xlsx"])

st.divider()

col1, col2 = st.columns(2)
with col1:
    hdr_meno = st.text_input("Meno zákazníka", "Jožko Mrkvička")
    hdr_sap  = st.text_input("SAP ID", "1090989")
with col2:
    hdr_ucet = st.text_input("Zmluvný účet", "777777777")
    hdr_spol = st.text_input("Názov spoločnosti", "SWAN a.s.")

export_choice = st.radio("Exportovať ako", ["XLS", "PDF", "Oboje"], horizontal=True)

# Voliteľná farebná schéma (môžeš ponechať „Firemná“)
theme_choice = st.radio(
    "Farebná schéma výstupu:", 
    ["Firemná (4ka tyrkys)"],  # neskôr: "Svetlá", "Tmavšia"
    horizontal=True
)
theme = "blue"  # firemná

st.divider()

# --- tlačidlo ---
if st.button("Generovať", use_container_width=True):
    try:
        # kontrola vstupov
        if not all([template, helper, src1, src2]):
            st.error("Nahraj všetky štyri XLS(X) súbory (template, pomôcka, vstup1, vstup2).")
            st.stop()

        # načítaj logo (pevné)
        logo_bytes = load_logo_bytes(DEFAULT_LOGO_PATH)
        if not logo_bytes:
            st.warning(f"Logo sa nepodarilo načítať z '{DEFAULT_LOGO_PATH}'. PDF sa vytvorí bez loga.")

        # načítaj súbory do bytes
        template_bytes = template.read()
        helper_bytes   = helper.read()
        src1_bytes     = src1.read()
        src2_bytes     = src2.read()

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

        # ak treba, vygeneruj PDF
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
