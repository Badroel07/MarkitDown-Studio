import sys
from pathlib import Path

# Pastikan module lokal converter dapat di-import
app_dir = Path(__file__).parent.resolve()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

import streamlit as st
from converter import DocumentConverter, DocumentConversionResult

# ==========================================
# Konfigurasi Halaman Streamlit
# ==========================================
st.set_page_config(
    page_title="MarkItDown Studio",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling modern & clean
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Familjen+Grotesk:ital,wght@0,400..700;1,400..700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    html, body, .stApp {
        font-family: 'Familjen Grotesk', sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6, p, label, button, input, textarea, select {
        font-family: 'Familjen Grotesk', sans-serif !important;
    }

    span:not([translate="no"]):not([data-testid*="Icon"]):not([data-testid*="icon"]) {
        font-family: 'Familjen Grotesk', sans-serif;
    }

    /* Kode tetap monospace */
    code, pre, .stCode, [data-testid="stCodeBlock"] * {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
    }

    /* Kembalikan font Material Symbols untuk semua icon Streamlit */
    [data-testid*="Icon"],
    [data-testid*="icon"],
    [data-testid="stIconMaterial"],
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stTooltipIcon"],
    span[translate="no"],
    .material-symbols-rounded,
    .material-icons,
    [class*="material-symbols"] {
        font-family: 'Material Symbols Rounded' !important;
    }

    h1 {
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }

    /* Sembunyikan tombol anchor link header */
    [data-testid="stHeaderActionElements"],
    [data-testid="stHeadingActionElements"],
    .anchor-link,
    a[aria-label="Link to heading"] {
        display: none !important;
    }

    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        background-color: #DBEAFE;
        color: #1D4ED8;
        margin-right: 4px;
        margin-bottom: 4px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# Inisialisasi Session State
# ==========================================
if "conversion_results" not in st.session_state:
    st.session_state["conversion_results"] = []
if "selected_file_idx" not in st.session_state:
    st.session_state["selected_file_idx"] = 0

# ==========================================
# Sidebar: Pengaturan & Opsi
# ==========================================
with st.sidebar:
    st.title(":material/settings: Pengaturan", anchor=False)

    st.subheader("Mesin Konverter", anchor=False)
    engine_label = st.radio(
        "Pilih Mesin:",
        options=["Microsoft MarkItDown", "IBM Docling"],
        index=0,
        help="Pilih parser dokumen yang digunakan untuk mengekstrak teks ke Markdown.",
    )
    is_docling = engine_label == "IBM Docling"
    selected_engine = (
        DocumentConverter.ENGINE_DOCLING if is_docling else DocumentConverter.ENGINE_MARKITDOWN
    )

    docling_installed = DocumentConverter.is_docling_available()
    if is_docling and not docling_installed:
        st.warning(
            "Pustaka `docling` belum terpasang. Jalankan perintah berikut di terminal:\n```bash\npip install docling\n```"
        )

    st.divider()

    st.subheader("Konfigurasi Format", anchor=False)
    add_frontmatter = st.toggle(
        "Sertakan YAML Frontmatter",
        value=True,
        help="Sisipkan metadata (nama file, tanggal, converter) di bagian paling atas markdown.",
    )

    enable_plugins = False
    use_ai = False
    openai_api_key = ""
    openai_base_url = ""
    llm_model = "gpt-4o"
    docling_compact_tables = False

    if not is_docling:
        enable_plugins = st.toggle(
            "Aktifkan Plugins Tambahan",
            value=True,
            help="Izinkan plugin MarkItDown pihak ketiga atau fitur tambahan.",
        )

        st.divider()

        st.subheader("Integrasi AI Vision / OCR (Opsional)", anchor=False)
        st.caption("Gunakan LLM untuk OCR gambar dalam PDF atau transkripsi audio.")
        use_ai = st.checkbox("Aktifkan Dukungan OpenAI / Vision", value=False)

        if use_ai:
            openai_api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-...",
                help="Masukkan API key OpenAI Anda.",
            )
            openai_base_url = st.text_input(
                "Base URL Kustom (Opsional)",
                placeholder="https://api.openai.com/v1",
                help="Kosongkan jika memakai endpoint resmi OpenAI. Bisa diisi untuk Ollama/Azure/LocalAI.",
            )
            llm_model = st.selectbox(
                "Model Vision / OCR",
                options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                index=0,
            )
    else:
        st.subheader("Opsi IBM Docling", anchor=False)
        docling_compact_tables = st.toggle(
            "Format Tabel Ringkas (Compact)",
            value=False,
            help="Hasilkan format tabel yang lebih ringkas dan hemat token.",
        )

    st.divider()

    with st.expander(":material/info: Format Dokumen Didukung"):
        if is_docling:
            st.markdown(
                """
                - **Dokumen Kantor**: PDF, DOCX, DOC, PPTX, PPT, XLSX, XLS
                - **Format Terbuka**: ODT, ODS, ODP, RTF, EPUB
                - **Teks & Data**: HTML, AsciiDoc (`.adoc`), Markdown (`.md`), Plain Text, CSV, XML, JSON
                - **Media**: Gambar (JPG, PNG, TIFF, BMP, WebP), Audio/Video
                """
            )
        else:
            st.markdown(
                """
                - **Dokumen Kantor**: PDF (`.pdf`), Word (`.docx`), Excel (`.xlsx`, `.xls`), PowerPoint (`.pptx`)
                - **Data & Teks**: CSV (`.csv`), JSON (`.json`), XML (`.xml`), Plain Text (`.txt`), RTF (`.rtf`)
                - **Web & Ebook**: HTML (`.html`, `.htm`), EPUB (`.epub`)
                - **Media & Arsip**: ZIP (`.zip`), Gambar (`.jpg`, `.png`), Audio (`.mp3`, `.wav`)
                """
            )

    powered_name = "IBM Docling" if is_docling else "microsoft/markitdown"
    powered_link = "https://github.com/DS4SD/docling" if is_docling else "https://github.com/microsoft/markitdown"
    st.caption(f"Powered by [{powered_name}]({powered_link})")

# Inisialisasi Converter Instance
try:
    converter = DocumentConverter(
        engine=selected_engine,
        enable_plugins=enable_plugins,
        openai_api_key=openai_api_key if use_ai else None,
        openai_base_url=openai_base_url if use_ai and openai_base_url else None,
        llm_model=llm_model if use_ai else None,
        docling_compact_tables=docling_compact_tables,
    )
    converter_init_error = None
except Exception as init_err:
    converter = None
    converter_init_error = str(init_err)

# ==========================================
# Main Content
# ==========================================
st.title("MarkItDown Studio", anchor=False)
st.markdown(
    "Konversi PDF, Word, PowerPoint, Excel, Gambar, Audio, dan Web ke format Markdown bersih bertenaga **Microsoft MarkItDown** & **IBM Docling**."
)

tab_upload, tab_url = st.tabs([":material/upload_file: Unggah File Dokumen", ":material/language: Konversi via URL Web"])

# ------------------------------------------
# TAB 1: UPLOAD FILE (Single / Batch)
# ------------------------------------------
with tab_upload:
    uploaded_files = st.file_uploader(
        "Pilih dokumen yang ingin dikonversi (bisa pilih banyak file sekaligus):",
        type=DocumentConverter.SUPPORTED_EXTENSIONS,
        accept_multiple_files=True,
        help="Format didukung: PDF, DOCX, PPTX, XLSX, XLS, CSV, JSON, XML, HTML, TXT, RTF, ZIP, EPUB, JPG, PNG, MP3, WAV.",
    )

    col_btn, col_clear = st.columns([2, 1])
    with col_btn:
        convert_clicked = st.button("Mulai Konversi Dokumen", icon=":material/rocket_launch:", type="primary", disabled=not uploaded_files)
    with col_clear:
        if st.session_state["conversion_results"]:
            if st.button("Bersihkan Hasil", icon=":material/delete_sweep:"):
                st.session_state["conversion_results"] = []
                st.session_state["selected_file_idx"] = 0
                st.rerun()

    if convert_clicked and uploaded_files:
        if converter is None:
            st.error(f"Gagal menginisialisasi mesin {engine_label}: {converter_init_error}")
        else:
            results = []
            progress_bar = st.progress(0, text="Menyiapkan konversi...")
            total_files = len(uploaded_files)

            with st.status(f"Sedang memproses dokumen dengan {engine_label}...", expanded=True) as status_box:
                for idx, file_obj in enumerate(uploaded_files):
                    fname = file_obj.name
                    status_box.write(f"Mengonversi: **{fname}** ({idx + 1}/{total_files})...")
                    file_bytes = file_obj.read()

                    res = converter.convert_file(
                        file_bytes=file_bytes,
                        filename=fname,
                        add_frontmatter=add_frontmatter,
                    )
                    results.append(res)
                    progress_bar.progress((idx + 1) / total_files, text=f"Selesai {idx + 1} dari {total_files} file.")

                status_box.update(label="Semua dokumen selesai diproses!", state="complete", expanded=False)

            st.session_state["conversion_results"] = results
            st.session_state["selected_file_idx"] = 0
            st.toast(f"Berhasil mengonversi {len(results)} dokumen!", icon=":material/check_circle:")

# ------------------------------------------
# TAB 2: KONVERSI DARI URL WEB
# ------------------------------------------
with tab_url:
    st.markdown("Masukkan URL halaman web, artikel, atau dokumen daring:")
    input_url = st.text_input("URL Target", placeholder="https://example.com/artikel")

    if st.button("Konversi URL ke Markdown", icon=":material/travel_explore:", type="primary", disabled=not input_url):
        if converter is None:
            st.error(f"Gagal menginisialisasi mesin {engine_label}: {converter_init_error}")
        else:
            with st.spinner(f"Mengunduh dan mengonversi {input_url} dengan {engine_label}..."):
                url_result = converter.convert_url(input_url, add_frontmatter=add_frontmatter)
                st.session_state["conversion_results"] = [url_result]
                st.session_state["selected_file_idx"] = 0
                if url_result.is_success:
                    st.toast("Konversi URL berhasil!", icon=":material/check_circle:")
                else:
                    st.error(f"Gagal mengonversi URL: {url_result.error}")

# ==========================================
# Area Tampilan Hasil Konversi
# ==========================================
results: list[DocumentConversionResult] = st.session_state.get("conversion_results", [])

if results:
    st.divider()
    st.subheader(":material/assignment: Hasil Konversi", anchor=False)
    st.caption(f"Mesin konversi aktif: **{engine_label}**")

    success_count = sum(1 for r in results if r.is_success)
    failed_count = len(results) - success_count
    total_tokens = sum(r.token_estimate for r in results if r.is_success)
    total_duration = sum(r.duration_seconds for r in results)

    # Ringkasan Metrik
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Berhasil", f"{success_count} / {len(results)}")
    with m2:
        st.metric("Estimasi Total Token", f"{total_tokens:,}")
    with m3:
        st.metric("Total Waktu Proses", f"{total_duration:.2f} s")
    with m4:
        if success_count > 1:
            zip_bytes = converter.create_zip_from_results(results)
            st.download_button(
                label="Unduh Semua (.ZIP)",
                data=zip_bytes,
                file_name="markitdown_results.zip",
                mime="application/zip",
                type="primary",
                icon=":material/folder_zip:",
            )
        elif success_count == 1:
            single = next(r for r in results if r.is_success)
            base_stem = Path(single.filename).stem or "converted"
            st.download_button(
                label="Unduh .MD",
                data=single.markdown,
                file_name=f"{base_stem}.md",
                mime="text/markdown",
                type="primary",
                icon=":material/download:",
            )

    # Navigasi Dokumen jika lebih dari 1
    if len(results) > 1:
        file_options = [
            f"{'✓' if r.is_success else '✗'} {Path(r.filename).name}"
            for r in results
        ]
        selected_label = st.selectbox(
            "Pilih dokumen untuk dilihat:",
            options=file_options,
            index=st.session_state.get("selected_file_idx", 0),
        )
        selected_idx = file_options.index(selected_label)
        st.session_state["selected_file_idx"] = selected_idx
    else:
        selected_idx = 0

    curr_res = results[selected_idx]

    if not curr_res.is_success:
        st.error(f"Gagal mengonversi **{curr_res.filename}**: {curr_res.error}")
    else:
        stem_name = Path(curr_res.filename).stem or "converted"
        md_filename = f"{stem_name}.md"

        tab_render, tab_raw, tab_info = st.tabs([":material/menu_book: Preview Markdown", ":material/edit_note: Raw Markdown / Editor", ":material/query_stats: Metadata"])

        with tab_render:
            col_preview_actions, _ = st.columns([1, 3])
            with col_preview_actions:
                st.download_button(
                    label=f"Unduh {md_filename}",
                    data=curr_res.markdown,
                    file_name=md_filename,
                    mime="text/markdown",
                    key=f"dl_preview_{selected_idx}",
                    icon=":material/download:",
                )
            st.markdown(curr_res.markdown)

        with tab_raw:
            col_raw_actions, _ = st.columns([1, 3])
            with col_raw_actions:
                st.download_button(
                    label=f"Unduh {md_filename}",
                    data=curr_res.markdown,
                    file_name=md_filename,
                    mime="text/markdown",
                    key=f"dl_raw_{selected_idx}",
                    icon=":material/download:",
                )
            st.text_area(
                "Teks Markdown Mentah:",
                value=curr_res.markdown,
                height=500,
                help="Anda dapat menyalin teks ini langsung.",
            )

        with tab_info:
            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            with col_i1:
                st.metric("Ukuran Asli", f"{curr_res.original_size / 1024:.1f} KB")
            with col_i2:
                st.metric("Jumlah Karakter", f"{curr_res.char_count:,}")
            with col_i3:
                st.metric("Jumlah Kata", f"{curr_res.word_count:,}")
            with col_i4:
                st.metric("Durasi Konversi", f"{curr_res.duration_seconds} s")
