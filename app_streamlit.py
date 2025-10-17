import streamlit as st
from pathlib import Path
from saldo_core import generate_saldo_xlsx

st.set_page_config(page_title="Saldo_1 report", page_icon="📄", layout="centered")

st.title("📄 Saldo_1 report – generátor")
st.caption("Template a Pomôcka sa berú z repozitára (data/). Nahraj len pohyby a väzby.")

colA, colB = st.columns(2)
with colA:
    hdr_meno = st.text_input("Meno zákazníka", value="", placeholder="Napr. Jozef Pučik")
    hdr_sap  = st.text_input("SAP ID", value="", placeholder="Napr. 111222547")
with colB:
    hdr_ucet = st.text_input("Číslo zmluvného účtu", value="", placeholder="Napr. 777777777")
    hdr_spol = st.text_input("Spoločnosť", value="SWAN a.s.")

st.markdown("### Súbory (len vstupy – pohyby & väzby)")
src1 = st.file_uploader("zdroj1.xlsx (pohyby)", type=["xlsx"])
src2 = st.file_uploader("zdroj2.xlsx (väzby)", type=["xlsx"])

with st.expander("Pokročilé: použiť vlastné TEMPLATE/POMÔCKA (voliteľné)"):
    use_custom = st.checkbox("Nahrať vlastné TEMPLATE/POMÔCKA")
    user_template = st.file_uploader("TEMPLATE_saldo.xlsx (voliteľné)", type=["xlsx"]) if use_custom else None
    user_helper   = st.file_uploader("pomocka k saldo (vlookup).xlsx (voliteľné)", type=["xlsx"]) if use_custom else None

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_TEMPLATE = (DATA_DIR / "TEMPLATE_saldo.XLSX").read_bytes() if (DATA_DIR / "TEMPLATE_saldo.XLSX").exists() else None
DEFAULT_HELPER   = (DATA_DIR / "pomocka k saldo (vlookup).XLSX").read_bytes() if (DATA_DIR / "pomocka k saldo (vlookup).XLSX").exists() else None

st.markdown("---")
if st.button("▶️ Generovať report"):
    missing = []
    if not hdr_meno: missing.append("Meno")
    if not hdr_sap:  missing.append("SAP ID")
    if not hdr_ucet: missing.append("Číslo zmluvného účtu")
    if not src1:     missing.append("zdroj1 (pohyby)")
    if not src2:     missing.append("zdroj2 (väzby)")

    template_bytes = user_template.read() if (use_custom and user_template) else DEFAULT_TEMPLATE
    helper_bytes   = user_helper.read()   if (use_custom and user_helper)   else DEFAULT_HELPER
    if not template_bytes: missing.append("TEMPLATE (data/TEMPLATE_saldo.XLSX)")
    if not helper_bytes:   missing.append("POMÔCKA (data/pomocka k saldo (vlookup).XLSX)")

    if missing:
        st.error("Chýbajú: " + ", ".join(missing))
    else:
        try:
            out_bytes = generate_saldo_xlsx(
                template_bytes, helper_bytes, src1.read(), src2.read(),
                hdr_meno=hdr_meno, hdr_sap=hdr_sap, hdr_ucet=hdr_ucet, hdr_spol=hdr_spol or "SWAN a.s."
            )
            out_name = f"{hdr_meno.strip().replace(' ', '_')}_saldo.xlsx"
            st.success("Hotovo ✅")
            st.download_button("📥 Stiahnuť výsledný Excel", data=out_bytes,
                               file_name=out_name,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Chyba pri generovaní: {e}")

st.caption("Tip: TEMPLATE/POMÔCKA spravuješ priamo v priečinku `data/` v repozitári.")
