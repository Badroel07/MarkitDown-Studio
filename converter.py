from __future__ import annotations

import csv
import io
import os
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


def _safe_decode_bytes(raw_bytes: bytes, charset: Optional[str] = None) -> str:
    candidates = []
    if charset:
        if charset.lower() == "ascii":
            candidates.extend(["utf-8", "utf-8-sig", "latin1", "cp1252"])
        else:
            candidates.append(charset)
    candidates.extend(["utf-8", "utf-8-sig", "cp1252", "latin1"])

    for enc in candidates:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw_bytes).best()
        if best is not None:
            return str(best)
    except Exception:
        pass

    return raw_bytes.decode("utf-8", errors="replace")


_markitdown_patched = False


def _patch_markitdown_encoding() -> None:
    global _markitdown_patched
    if _markitdown_patched:
        return
    try:
        import markitdown._markitdown as md_module

        # 1. Normalize "ascii" guesses to "utf-8" so 4KB ASCII chunk doesn't force ASCII decoding
        orig_norm = md_module.MarkItDown._normalize_charset

        def patched_normalize(self, charset):
            norm = orig_norm(self, charset)
            if norm and norm.lower() == "ascii":
                return "utf-8"
            return norm

        md_module.MarkItDown._normalize_charset = patched_normalize

        # 2. Patch CsvConverter.convert to safely decode stream
        def patched_csv_convert(self, file_stream, stream_info, **kwargs):
            raw = file_stream.read()
            content = _safe_decode_bytes(raw, getattr(stream_info, "charset", None))
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if not rows:
                return md_module.DocumentConverterResult(markdown="")
            markdown_table = []
            markdown_table.append("| " + " | ".join(rows[0]) + " |")
            markdown_table.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
            for row in rows[1:]:
                while len(row) < len(rows[0]):
                    row.append("")
                row = row[: len(rows[0])]
                markdown_table.append("| " + " | ".join(row) + " |")
            return md_module.DocumentConverterResult(markdown="\n".join(markdown_table))

        md_module.CsvConverter.convert = patched_csv_convert

        # 3. Patch PlainTextConverter.convert to safely decode stream
        def patched_plain_convert(self, file_stream, stream_info, **kwargs):
            raw = file_stream.read()
            content = _safe_decode_bytes(raw, getattr(stream_info, "charset", None))
            return md_module.DocumentConverterResult(markdown=content)

        md_module.PlainTextConverter.convert = patched_plain_convert

        _markitdown_patched = True
    except Exception as e:
        print(f"Warning: Failed to patch MarkItDown encoding: {e}")


_patch_markitdown_encoding()


@dataclass
class DocumentConversionResult:
    filename: str
    markdown: str
    original_size: int
    char_count: int
    word_count: int
    token_estimate: int
    duration_seconds: float
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None and bool(self.markdown)


class DocumentConverter:
    SUPPORTED_EXTENSIONS = [
        "pdf",
        "docx",
        "pptx",
        "xlsx",
        "xls",
        "csv",
        "json",
        "xml",
        "html",
        "htm",
        "txt",
        "rtf",
        "jpg",
        "jpeg",
        "png",
        "mp3",
        "wav",
        "zip",
        "epub",
        "adoc",
        "asciidoc",
        "md",
    ]

    ENGINE_MARKITDOWN = "markitdown"
    ENGINE_DOCLING = "docling"

    @classmethod
    def is_docling_available(cls) -> bool:
        try:
            import docling  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def is_markitdown_available(cls) -> bool:
        try:
            import markitdown  # noqa: F401
            return True
        except ImportError:
            return False

    def __init__(
        self,
        engine: str = ENGINE_MARKITDOWN,
        enable_plugins: bool = True,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
        docling_compact_tables: bool = False,
    ) -> None:
        self.engine = engine.lower().strip()
        self.enable_plugins = enable_plugins
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url
        self.llm_model = llm_model or "gpt-4o"
        self.docling_compact_tables = docling_compact_tables

        self._md = None
        self._docling = None

        if self.engine == self.ENGINE_DOCLING:
            self._docling = self._build_docling()
        else:
            self._md = self._build_markitdown()

    def _build_docling(self):
        try:
            from docling.document_converter import DocumentConverter as DoclingConverter
            return DoclingConverter()
        except ImportError as e:
            raise ImportError(
                "Pustaka 'docling' belum terpasang di sistem. Pasang menggunakan perintah: pip install docling"
            ) from e

    def _build_markitdown(self):
        from markitdown import MarkItDown

        llm_client = None
        if self.openai_api_key and self.openai_api_key.strip():
            try:
                from openai import OpenAI

                client_kwargs = {"api_key": self.openai_api_key.strip()}
                if self.openai_base_url and self.openai_base_url.strip():
                    client_kwargs["base_url"] = self.openai_base_url.strip()
                llm_client = OpenAI(**client_kwargs)
            except Exception as e:
                # Fallback to no LLM client if init fails
                print(f"Warning: Failed to initialize LLM client: {e}")
                llm_client = None

        init_kwargs = {"enable_plugins": self.enable_plugins}
        if llm_client:
            init_kwargs["llm_client"] = llm_client
            init_kwargs["llm_model"] = self.llm_model

        return MarkItDown(**init_kwargs)

    def _clean_markdown(self, text: str) -> str:
        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove consecutive blank lines (> 2)
        lines = text.split("\n")
        cleaned_lines = []
        blank_streak = 0
        for line in lines:
            if not line.strip():
                blank_streak += 1
                if blank_streak <= 2:
                    cleaned_lines.append(line)
            else:
                blank_streak = 0
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _attach_frontmatter(self, text: str, filename: str, source_type: str = "file") -> str:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        engine_label = "IBM Docling" if self.engine == self.ENGINE_DOCLING else "Microsoft MarkItDown"
        frontmatter = (
            f"---\n"
            f"source_name: \"{filename}\"\n"
            f"source_type: \"{source_type}\"\n"
            f"converted_at: \"{now_str}\"\n"
            f"converted_by: \"{engine_label}\"\n"
            f"---\n\n"
        )
        return frontmatter + text

    def convert_file(
        self,
        file_bytes: bytes,
        filename: str,
        add_frontmatter: bool = True,
    ) -> DocumentConversionResult:
        start_time = time.perf_counter()
        original_size = len(file_bytes)
        safe_name = Path(filename).name

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_file_path = os.path.join(tmp_dir, safe_name)
                with open(temp_file_path, "wb") as f:
                    f.write(file_bytes)

                if self.engine == self.ENGINE_DOCLING:
                    if self._docling is None:
                        self._docling = self._build_docling()
                    conv_res = self._docling.convert(temp_file_path)
                    markdown_content = conv_res.document.export_to_markdown(
                        compact_tables=self.docling_compact_tables
                    )
                else:
                    if self._md is None:
                        self._md = self._build_markitdown()
                    raw_result = self._md.convert(temp_file_path)
                    markdown_content = getattr(raw_result, "text_content", None)
                    if markdown_content is None:
                        markdown_content = getattr(raw_result, "markdown", str(raw_result))

                markdown_content = self._clean_markdown(markdown_content)

                if add_frontmatter:
                    markdown_content = self._attach_frontmatter(
                        markdown_content, safe_name, source_type="file"
                    )

                duration = time.perf_counter() - start_time
                char_count = len(markdown_content)
                word_count = len(markdown_content.split())
                token_estimate = max(1, char_count // 4)

                return DocumentConversionResult(
                    filename=filename,
                    markdown=markdown_content,
                    original_size=original_size,
                    char_count=char_count,
                    word_count=word_count,
                    token_estimate=token_estimate,
                    duration_seconds=round(duration, 3),
                )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            return DocumentConversionResult(
                filename=filename,
                markdown="",
                original_size=original_size,
                char_count=0,
                word_count=0,
                token_estimate=0,
                duration_seconds=round(duration, 3),
                error=str(exc),
            )

    def convert_url(
        self,
        url: str,
        add_frontmatter: bool = True,
    ) -> DocumentConversionResult:
        start_time = time.perf_counter()
        try:
            if self.engine == self.ENGINE_DOCLING:
                if self._docling is None:
                    self._docling = self._build_docling()
                conv_res = self._docling.convert(url)
                markdown_content = conv_res.document.export_to_markdown(
                    compact_tables=self.docling_compact_tables
                )
            else:
                if self._md is None:
                    self._md = self._build_markitdown()
                raw_result = self._md.convert(url)
                markdown_content = getattr(raw_result, "text_content", None)
                if markdown_content is None:
                    markdown_content = getattr(raw_result, "markdown", str(raw_result))

            markdown_content = self._clean_markdown(markdown_content)

            if add_frontmatter:
                markdown_content = self._attach_frontmatter(
                    markdown_content, url, source_type="url"
                )

            duration = time.perf_counter() - start_time
            char_count = len(markdown_content)
            word_count = len(markdown_content.split())
            token_estimate = max(1, char_count // 4)

            return DocumentConversionResult(
                filename=url,
                markdown=markdown_content,
                original_size=char_count,
                char_count=char_count,
                word_count=word_count,
                token_estimate=token_estimate,
                duration_seconds=round(duration, 3),
            )
        except Exception as exc:
            duration = time.perf_counter() - start_time
            return DocumentConversionResult(
                filename=url,
                markdown="",
                original_size=0,
                char_count=0,
                word_count=0,
                token_estimate=0,
                duration_seconds=round(duration, 3),
                error=str(exc),
            )

    @staticmethod
    def create_zip_from_results(results: list[DocumentConversionResult]) -> bytes:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for item in results:
                if item.is_success:
                    base_name = Path(item.filename).stem or "converted"
                    out_filename = f"{base_name}.md"
                    zip_file.writestr(out_filename, item.markdown.encode("utf-8"))
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
