
import streamlit as st
from saldo_core import generate_saldo_xlsx

st.set_page_config(page_title="Saldo_1 report", page_icon="📄")

st.title("📄 Saldo_1 report – generátor")

colA, colB = st.columns(2)
with colA:
    hdr_meno = st.text_input("Meno zákazníka", value="")
    hdr_sap  = st.text_input("SAP ID", value="")
with colB:
    hdr_ucet = st.text_input("Číslo zmluvného účtu", value="")
    hdr_spol = st.text_input("Spoločnosť", value="SWAN a.s.")

st.markdown("---")
st.subheader("Súbory")
template = st.file_uploader("TEMPLATE_saldo.xlsx", type=["xlsx"], accept_multiple_files=False)
helper   = st.file_uploader("pomocka k saldo (vlookup).xlsx", type=["xlsx"], accept_multiple_files=False)
src1     = st.file_uploader("zdroj1.xlsx (pohyby)", type=["xlsx"], accept_multiple_files=False)
src2     = st.file_uploader("zdroj2.xlsx (väzby)", type=["xlsx"], accept_multiple_files=False)

run = st.button("▶️ Generovať report")

if run:
    missing = []
    if not template: missing.append("TEMPLATE")
    if not helper:   missing.append("pomôcka")
    if not src1:     missing.append("zdroj1 (pohyby)")
    if not src2:     missing.append("zdroj2 (väzby)")
    if not hdr_meno: missing.append("Meno")
    if not hdr_sap:  missing.append("SAP ID")
    if not hdr_ucet: missing.append("Číslo zmluvného účtu")

    if missing:
        st.error("Chýbajú: " + ", ".join(missing))
    else:
        try:
            out_bytes = generate_saldo_xlsx(
                template.read(),
                helper.read(),
                src1.read(),
                src2.read(),
                hdr_meno=hdr_meno,
                hdr_sap=hdr_sap,
                hdr_ucet=hdr_ucet,
                hdr_spol=hdr_spol or "SWAN a.s.",
            )
            out_name = f"{hdr_meno.strip().replace(' ', '_')}_saldo.xlsx"
            st.success("Hotovo. Stiahni výsledok nižšie.")
            st.download_button(
                "📥 Stiahnuť výsledný Excel",
                data=out_bytes,
                file_name=out_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Chyba pri generovaní: {e}")
