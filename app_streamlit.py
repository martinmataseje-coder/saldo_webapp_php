import io, os, datetime as dt
import streamlit as st

from saldo_core import generate_saldo_xlsx, generate_saldo_pdf

st.set_page_config(page_title="Saldo generátor", page_icon="📄", layout="centered")
st.title("Saldo – generátor")

# ---- Uploady / vstupy ----
template = st.file_uploader("TEMPLATE_saldo.xlsx", type=["xlsx"])
helper   = st.file_uploader("pomocka_saldo.xlsx", type=["xlsx"])
src1     = st.file_uploader("Vstupný súbor 1", type=["xlsx"])
src2     = st.file_uploader("Vstupný súbor 2", type=["xlsx"])

colA, colB = st.columns(2)
with colA:
    hdr_meno = st.text_input("Meno zákazníka", "Jožko Mrkvička")
    hdr_sap  = st.text_input("SAP ID", "1090989")
with colB:
    hdr_ucet = st.text_input("Zmluvný účet", "777777777")
    hdr_spol = st.text_input("Názov spoločnosti", "SWAN a.s.")

export_choice = st.radio("Exportovať ako", ["XLS", "PDF", "Oboje"], horizontal=True)

logo_path_default = "data/logo_4ka_circle.png"
logo_path = st.text_input("Cesta k logu", logo_path_default)

st.divider()

# ---- Spustiť generovanie ----
if st.button("Generovať"):
    if not all([template, helper, src1, src2]):
        st.error("Nahraj všetky štyri XLS(X) súbory (template, pomôcka, vstup1, vstup2).")
        st.stop()

    # 1️⃣ Generovanie XLS
    xls_bytes = generate_saldo_xlsx(
        template.read(),
        helper.read(),
        src1.read(),
        src2.read(),
        hdr_meno,
        hdr_sap,
        hdr_ucet,
        hdr_spol
    )

    safe_name = hdr_meno.strip().replace(" ", "_")
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "data"
    os.makedirs(out_dir, exist_ok=True)
    xls_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.xlsx")
    pdf_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.pdf")

    # uložiť XLS (potrebné pre PDF)
    with open(xls_path, "wb") as f:
        f.write(xls_bytes)

    st.success(f"✅ XLS vygenerovaný: {xls_path}")

    # 2️⃣ Ak si zvolil PDF / Oboje → generuj PDF
    pdf_bytes = None
    if export_choice in ("PDF", "Oboje"):
        if not os.path.exists(logo_path):
            st.warning(f"Logo nenájdené: {logo_path}")
        else:
            generate_saldo_pdf(xls_path, logo_path, pdf_path)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.success(f"✅ PDF vygenerované: {pdf_path}")

    # 3️⃣ Tlačidlá na stiahnutie
    st.write("### Stiahnuť výstupy")
    if export_choice in ("XLS", "Oboje"):
        st.download_button(
            "⬇️ Stiahnuť XLS",
            data=xls_bytes,
            file_name=os.path.basename(xls_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    if export_choice in ("PDF", "Oboje") and pdf_bytes:
        st.download_button(
            "⬇️ Stiahnuť PDF",
            data=pdf_bytes,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            use_container_width=True
        )
