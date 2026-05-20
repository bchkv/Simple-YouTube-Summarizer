from pathlib import Path

from summarizer.config import Settings

_MIN_CHARS_PER_PAGE = 40


def _extract_embedded_text(path: Path) -> tuple[str, int]:
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError(
            "PDF support requires PyMuPDF. Install with: pip install -e '.[pdf]'."
        ) from e

    doc = fitz.open(path)
    try:
        pages = [page.get_text("text").strip() for page in doc]
    finally:
        doc.close()

    page_count = len(pages)
    text = "\n\n".join(p for p in pages if p).strip()
    return text, page_count


def _ocr_pdf(path: Path, settings: Settings, *, quiet: bool) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        raise RuntimeError(
            "PDF OCR requires pdf2image and pytesseract. "
            "Install with: pip install -e '.[pdf]' and system tools "
            "tesseract + poppler (e.g. brew install tesseract poppler)."
        ) from e

    if not quiet:
        print(f"OCR scanning PDF ({settings.pdf_ocr_dpi} dpi)…", file=sys.stderr)

    images = convert_from_path(str(path), dpi=settings.pdf_ocr_dpi)
    lang = settings.pdf_ocr_language
    texts: list[str] = []
    for i, image in enumerate(images, 1):
        if not quiet:
            print(f"OCR page {i}/{len(images)}…", file=sys.stderr)
        if lang:
            texts.append(pytesseract.image_to_string(image, lang=lang))
        else:
            texts.append(pytesseract.image_to_string(image))

    return "\n\n".join(t.strip() for t in texts if t.strip()).strip()


def _needs_ocr(text: str, page_count: int, settings: Settings) -> bool:
    if settings.pdf_force_ocr:
        return True
    if page_count == 0:
        return True
    return len(text) < _MIN_CHARS_PER_PAGE * page_count


class PdfFileExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, source: str, *, quiet: bool = False) -> str:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {path}")

        if not quiet:
            print(f"Reading PDF: {path.name}", file=sys.stderr)

        embedded, page_count = _extract_embedded_text(path)
        if _needs_ocr(embedded, page_count, self._settings):
            if embedded and not quiet:
                print(
                    "Little or no embedded text found; using OCR…",
                    file=sys.stderr,
                )
            text = _ocr_pdf(path, self._settings, quiet=quiet)
        else:
            if not quiet:
                print(
                    f"Using embedded PDF text ({page_count} pages, "
                    f"{len(embedded):,} chars)",
                    file=sys.stderr,
                )
            text = embedded

        if not text:
            raise RuntimeError("No text extracted from PDF.")
        return text
