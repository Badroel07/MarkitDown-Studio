# MarkItDown Studio (Streamlit UI)

Aplikasi konversi berbagai format dokumen menjadi Markdown bersih dan terstruktur dengan dukungan dual engine: **Microsoft MarkItDown** dan **IBM Docling**, dilengkapi antarmuka interaktif **Streamlit**.

## 🚀 Fitur Utama
- **Dukungan Dual Engine Konversi**:
  - **Microsoft MarkItDown**: Cepat dan fleksibel, mendukung ragam dokumen kantor, arsip, audio, serta integrasi OpenAI Vision/OCR.
  - **IBM Docling**: Ekstraksi presisi tinggi untuk PDF, tabel kompleks, dokumen ilmiah/teknis, dan ragam format data.
- **Mendukung Ragam Format**:
  - Dokumen kantor: PDF, Word (`.docx`, `.doc`), Excel (`.xlsx`, `.xls`), PowerPoint (`.pptx`, `.ppt`), ODT, ODS, ODP.
  - Teks & Data: CSV, JSON, XML, HTML, Plain Text, RTF, AsciiDoc, LaTeX.
  - Media & Ebook: Audio (`.mp3`, `.wav`), Gambar (`.jpg`, `.png`, `.webp`, `.tiff`), EPUB, ZIP.
- **Konversi Batch & Single**: Unggah banyak dokumen sekaligus dalam sekali klik.
- **Konversi URL Langsung**: Ambil dan ubah halaman web menjadi Markdown secara instan.
- **Preview Interaktif**:
  - Preview Markdown yang ter-render rapi.
  - Tampilan Markdown mentah dengan editor/textarea.
  - Ringkasan metrik (estimasi token LLM, jumlah karakter, kata, dan waktu proses).
- **Ekspor Fleksibel**:
  - Download file individual `.md`.
  - Download gabungan semua hasil konversi sebagai arsip `.zip`.
- **Integrasi AI / OCR Opsional**: Konfigurasi OpenAI API Key atau endpoint lokal (Ollama / LocalAI) untuk deskripsi visual dan transkripsi audio.

---

## 🛠️ Cara Instalasi & Menjalankan

### 1. Instal Dependensi
Pastikan virtual environment aktif, lalu jalankan:
```bash
pip install -r markitdown_app/requirements.txt
```

Jika ingin menggunakan engine **IBM Docling**, pastikan paket `docling` terpasang:
```bash
pip install docling
```

### 2. Jalankan Aplikasi
Jalankan melalui Streamlit:
```bash
streamlit run markitdown_app/app.py
```

Atau di Windows, cukup klik dua kali file `run_converter.bat`.
Aplikasi akan terbuka otomatis di peramban Anda pada alamat `http://localhost:8501`.
