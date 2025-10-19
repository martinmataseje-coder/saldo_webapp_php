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

# bezpečný import core
try:
    from saldo_core import generate_saldo_document
except Exception as e:
    st.error("Nepodarilo sa načítať modul `saldo_core.py`.")
    st.exception(e)
    st.stop()

# --- init session defaults ---
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "auto_clear" not in st.session_state:
    st.session_state.auto_clear = True

def clear_inputs():
    # ŽIADNE priame nastavovanie widgetov! Len zvýšime reset token:
    st.session_state.reset_counter += 1

rc = st.session_state.reset_counter  # použijeme v kľúčoch

# --- Uploady (len 2 vstupy) ---
with st.container():
    colA, colB = st.columns(2)
    with colA:
        src1 = st.file_uploader(
            "Vstup 1 (pohyby)",
            type=["xlsx"],
            key=f"src1_{rc}",
            help="Nahraj XLSX s položkami/pohybmi."
        )
    with colB:
        src2 = st.file_uploader(
            "Vstup 2 (väzby)",
            type=["xlsx"],
            key=f"src2_{rc}",
            help="Nahraj XLSX, kde je 'Doplnková referencia' (stĺpec G)."
        )

st.caption("Template a Pomôcka sa načítajú automaticky z priečinka `data/`.")
st.divider()

# --- Textové polia (bez spoločnosti – tá je fixne 'SWAN a.s.') ---
col1, col2 = st.columns(2)
with col1:
    hdr_meno = st.text_input("Meno zákazníka", key=f"hdr_meno_{rc}", placeholder="napr. Jožko Mrkvička")
    hdr_sap  = st.text_input("SAP ID",         key=f"hdr_sap_{rc}",  placeholder="napr. 1090989")
with col2:
    hdr_ucet = st.text_input("Zmluvný účet",   key=f"hdr_ucet_{rc}", placeholder="napr. 777777777")

# pevná spoločnosť
hdr_spol = "SWAN a.s."

# Výber farebnej schémy (tiež viazaný na reset token)
theme = st.radio(
    "Farebná schéma výstupu:",
    ["blue", "gray", "warm"],
    key=f"theme_{rc}",
    format_func=lambda x: {
        "blue": "Firemná (4ka tyrkys)",
        "gray": "Svetlá (sivá)",
        "warm": "Teplá (béžová)"
    }[x],
    horizontal=True
)

# Ovládanie vymazania polí
col_reset_left, col_reset_right = st.columns([1, 1])
with col_reset_left:
    auto_clear = st.checkbox("Vymazať polia po generovaní", key="auto_clear", value=st.session_state.auto_clear)
with col_reset_right:
    if st.button("Vymazať polia teraz"):
        clear_inputs()
        st.rerun()  # okamžitý refresh UI

st.divider()

# Vždy generujeme OBOJE (XLS aj PDF)
if st.button("Generovať", use_container_width=True, key=f"gen_{rc}"):
    try:
        # validácia vstupov (povinné)
        missing = []
        if not src1: missing.append("Vstup 1 (pohyby)")
        if not src2: missing.append("Vstup 2 (väzby)")
        if not (hdr_meno or "").strip(): missing.append("Meno zákazníka")
        if not (hdr_sap or "").strip():  missing.append("SAP ID")
        if not (hdr_ucet or "").strip(): missing.append("Zmluvný účet")

        if missing:
            st.error("Doplň povinné polia: " + ", ".join(missing))
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

        # logo (pevné)
        logo_bytes = load_file_bytes(DEFAULT_LOGO_PATH)
        if not logo_bytes:
            st.warning(f"Logo sa nepodarilo načítať z '{DEFAULT_LOGO_PATH}'. PDF sa vytvorí bez loga.")

        # bytes z uploadov
        src1_bytes = src1.read()
        src2_bytes = src2.read()

        # cesty na uloženie
        safe_name = (hdr_meno or "").strip().replace(" ", "_") or "report"
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = "data"
        os.makedirs(out_dir, exist_ok=True)
        xls_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.xlsx")
        pdf_path = os.path.join(out_dir, f"{safe_name}_saldo_{ts}.pdf")

        # ===== XLS =====
        xls_bytes = generate_saldo_document(
            template_bytes, helper_bytes, src1_bytes, src2_bytes,
            hdr_meno=(hdr_meno or "").strip(),
            hdr_sap=(hdr_sap or "").strip(),
            hdr_ucet=(hdr_ucet or "").strip(),
            hdr_spol=hdr_spol,
            theme=theme, logo_bytes=logo_bytes, output="xlsx"
        )
        with open(xls_path, "wb") as f:
            f.write(xls_bytes)
        st.success(f"✅ XLS vygenerovaný: {xls_path}")

        # ===== PDF =====
        pdf_bytes = generate_saldo_document(
            template_bytes, helper_bytes, src1_bytes, src2_bytes,
            hdr_meno=(hdr_meno or "").strip(),
            hdr_sap=(hdr_sap or "").strip(),
            hdr_ucet=(hdr_ucet or "").strip(),
            hdr_spol=hdr_spol,
            theme=theme, logo_bytes=logo_bytes, output="pdf"
        )
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        st.success(f"✅ PDF vygenerované: {pdf_path}")

        # ===== sťahovanie =====
        st.write("### Stiahnuť výstupy")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "⬇️ Stiahnuť XLS",
                data=xls_bytes,
                file_name=os.path.basename(xls_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_dl2:
            st.download_button(
                "⬇️ Stiahnuť PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True
            )

        # Auto-clear po úspešnom generovaní (ak je zapnuté)
        if auto_clear:
            clear_inputs()
            st.rerun()

    except Exception as e:
        st.error("Pri generovaní nastala chyba.")
        st.exception(e)
