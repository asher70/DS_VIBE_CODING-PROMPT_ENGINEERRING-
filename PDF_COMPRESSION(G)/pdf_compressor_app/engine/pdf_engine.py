from __future__ import annotations

import gc
import io
import os
from typing import Callable

import fitz
import psutil
from PIL import Image


COMPRESSION_LEVELS = {
    "1": {"name": "Best Quality", "scale": 1.0, "jpeg_quality": 90},
    "2": {"name": "Balanced", "scale": 0.75, "jpeg_quality": 75},
    "3": {"name": "Smallest Size", "scale": 0.5, "jpeg_quality": 55},
}


ProgressCallback = Callable[[int, int, str], None]
CancelCheck = Callable[[], bool]


class PdfEngineError(Exception):
    """Base error raised by the compression engine."""


class InvalidPdfError(PdfEngineError):
    """Raised when a PDF cannot be opened or parsed."""


class PasswordProtectedPdfError(PdfEngineError):
    """Raised when a PDF needs a password."""


class UnsupportedPdfError(PdfEngineError):
    """Raised when the PDF structure cannot be safely processed."""


class LowMemoryError(PdfEngineError):
    """Raised when the computer does not have enough free memory."""


class SavePdfError(PdfEngineError):
    """Raised when the compressed PDF cannot be saved."""


class CompressionCancelledError(PdfEngineError):
    """Raised when the user cancels compression."""


def log_memory(prefix: str = "") -> str:
    mem = psutil.virtual_memory()
    message = f"{prefix} RAM: {mem.percent}% used"
    print(message)
    return message


def validate_pdf(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError("PDF file not found.")
    if os.path.getsize(path) == 0:
        raise ValueError("Uploaded PDF is empty.")


def output_name(input_path: str) -> str:
    base = os.path.basename(input_path)
    if base.lower().endswith(".pdf"):
        base = base[:-4]
    return f"{base}_compressed.pdf"


def xref_has_mask(doc: fitz.Document, xref: int) -> bool:
    """
    Detect common transparency/mask indicators in the PDF image object dictionary.
    This is a heuristic, but it helps avoid black rectangle corruption.
    """
    try:
        obj = doc.xref_object(xref, compressed=False)
        return ("/SMask" in obj) or ("/Mask" in obj)
    except Exception:
        return False


def pil_from_pixmap(pix: fitz.Pixmap) -> Image.Image:
    """
    Convert PyMuPDF Pixmap to PIL Image.
    """
    mode = "RGBA" if pix.alpha else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)


def encode_image(img: Image.Image, force_png: bool, jpeg_quality: int) -> bytes:
    """
    Encode PIL image to PNG for alpha/mask safety or JPEG for smaller opaque images.
    """
    buf = io.BytesIO()
    if force_png:
        img.save(buf, format="PNG", optimize=True)
    else:
        img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
    return buf.getvalue()


def resize_if_needed(img: Image.Image, scale: float) -> Image.Image:
    """
    Downscale image to reduce size while keeping readability.
    """
    if scale >= 1.0:
        return img
    new_w = max(1, int(img.size[0] * scale))
    new_h = max(1, int(img.size[1] * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def _check_memory() -> None:
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    if available_mb < 150:
        raise LowMemoryError(
            "Not enough free memory is available to safely continue compression."
        )


def _raise_if_cancelled(cancel_check: CancelCheck | None) -> None:
    if cancel_check is not None and cancel_check():
        raise CompressionCancelledError("Compression was cancelled by the user.")


def _emit_progress(
    progress_callback: ProgressCallback | None,
    current: int,
    total: int,
    message: str,
) -> None:
    print(message)
    if progress_callback is not None:
        progress_callback(current, total, message)


def compress_pdf_safe(
    input_pdf: str,
    output_pdf: str,
    level_key: str,
    progress_callback: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> None:
    """
    Compress images safely while preserving text/layout.

    This keeps the existing backend approach:
    - open with PyMuPDF
    - inspect images per page
    - preserve alpha/mask images as PNG
    - compress opaque images as JPEG
    - replace images with Page.replace_image
    - save with garbage collection, deflate, and clean enabled
    """
    try:
        validate_pdf(input_pdf)
    except FileNotFoundError:
        raise
    except ValueError as exc:
        raise InvalidPdfError(str(exc)) from exc

    if level_key not in COMPRESSION_LEVELS:
        raise ValueError("Invalid compression level.")

    cfg = COMPRESSION_LEVELS[level_key]
    scale = cfg["scale"]
    jpeg_q = cfg["jpeg_quality"]
    doc: fitz.Document | None = None

    try:
        _check_memory()
        _raise_if_cancelled(cancel_check)

        _emit_progress(progress_callback, 0, 1, f"Opening PDF: {input_pdf}")
        doc = fitz.open(input_pdf)

        if doc.needs_pass:
            raise PasswordProtectedPdfError(
                "This PDF is password-protected or encrypted."
            )

        total_pages = len(doc)
        if total_pages <= 0:
            raise UnsupportedPdfError("This PDF does not contain any pages.")

        replaced = 0
        skipped = 0

        for pno in range(total_pages):
            _check_memory()
            _raise_if_cancelled(cancel_check)

            page = doc[pno]
            images = page.get_images(full=True)

            _emit_progress(
                progress_callback,
                pno,
                total_pages,
                f"Page {pno + 1}/{total_pages}: images found: {len(images)}",
            )

            seen = set()

            for info in images:
                _raise_if_cancelled(cancel_check)

                xref = info[0]
                if xref in seen:
                    continue
                seen.add(xref)

                try:
                    pix = fitz.Pixmap(doc, xref)

                    if pix.n >= 5 and not pix.alpha:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    risky = pix.alpha or xref_has_mask(doc, xref)
                    img = pil_from_pixmap(pix)
                    img = resize_if_needed(img, scale=scale)
                    data = encode_image(img, force_png=risky, jpeg_quality=jpeg_q)

                    page.replace_image(xref, stream=data)
                    replaced += 1

                except Exception as exc:
                    skipped += 1
                    print(f"  - Skipped image xref={xref}: {exc}")

                finally:
                    gc.collect()

            log_memory(prefix="After page")
            _emit_progress(
                progress_callback,
                pno + 1,
                total_pages,
                f"Processed page {pno + 1}/{total_pages}",
            )

        _raise_if_cancelled(cancel_check)
        _emit_progress(progress_callback, total_pages, total_pages, "Saving optimized PDF...")

        try:
            doc.save(output_pdf, garbage=4, deflate=True, clean=True)
        except Exception as exc:
            raise SavePdfError(f"Could not save compressed PDF: {exc}") from exc

        _emit_progress(
            progress_callback,
            total_pages,
            total_pages,
            f"Done. Images replaced: {replaced}, skipped: {skipped}",
        )

    except PdfEngineError:
        raise
    except MemoryError as exc:
        raise LowMemoryError("The computer ran out of memory during compression.") from exc
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise InvalidPdfError(f"Could not process this PDF: {exc}") from exc
    finally:
        if doc is not None:
            doc.close()

