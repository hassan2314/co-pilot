"""Turn an uploaded PDF, TXT, or Markdown file into plain text."""

from io import BytesIO
from pathlib import Path

from app.settings import max_upload_bytes

ALLOWED = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}

MAX_TEXT_CHARS = 200_000


class UploadError(ValueError):
    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def clean_filename(name: str) -> str:
    base = Path(name or "").name.replace("\\", "/").split("/")[-1].strip()
    cleaned = []
    for char in base:
        if char.isalnum() or char in "._- ":
            cleaned.append(char)
        else:
            cleaned.append("-")
    base = "".join(cleaned).strip(" .-")
    if not base or base in {".", ".."}:
        raise UploadError("filename is empty")
    if len(base) > 180:
        stem, dot, ext = base.rpartition(".")
        if dot:
            base = f"{(stem or 'file')[:160]}.{ext[:10]}"
        else:
            base = base[:180]
    return base


def prepare_upload(filename: str, data: bytes) -> tuple[str, str, str]:
    if len(data) > max_upload_bytes():
        limit = max_upload_bytes() // (1024 * 1024)
        raise UploadError(f"{filename or 'file'} is larger than {limit} MB", code=413)
    if not data:
        raise UploadError(f"{filename or 'file'} is empty")

    safe = clean_filename(filename)
    ext = Path(safe).suffix.lower()
    kind = ALLOWED.get(ext)
    if kind is None:
        raise UploadError(
            f"{safe} is not a supported type. Upload PDF, TXT, or Markdown.",
            code=415,
        )

    if kind == "pdf":
        text = _pdf_text(data, safe)
    else:
        text = _decode_text(data)

    text = text.replace("\x00", "").strip()
    if not text:
        raise UploadError(f"no text found in {safe}")
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    return safe, kind, text


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pdf_text(data: bytes, name: str) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(BytesIO(data))
    except PdfReadError as exc:
        raise UploadError(f"{name} is not a readable PDF") from exc
    if reader.is_encrypted:
        raise UploadError(f"{name} is encrypted. Upload an unlocked PDF.")

    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages)
