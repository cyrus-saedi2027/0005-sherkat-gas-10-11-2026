"""Image intake: validate by decoding (never trust extension/Content-Type), cap pixels,
read EXIF capture time, strip metadata by re-encoding, make a thumbnail (R12, R36)."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, datetime

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import AppError

try:  # HEIC from iPhones
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - optional codec
    pass

MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # decompression-bomb guard
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC", "MPO"}
MAX_EDGE = 2560
THUMB_EDGE = 480


@dataclass
class ProcessedImage:
    data: bytes
    thumb: bytes
    mime: str
    width: int
    height: int
    sha256: str  # of the ORIGINAL bytes — duplicate-photo detection must see the user's file
    exif_taken_at: datetime | None


def _exif_datetime(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
        if not raw:
            return None
        # EXIF has no timezone; phones write local (Tehran) time — store as naive→Tehran→UTC.
        from app.core.jalali import TEHRAN

        return datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S").replace(tzinfo=TEHRAN).astimezone(UTC)
    except Exception:
        return None


def process_image(raw: bytes, max_bytes: int) -> ProcessedImage:
    if len(raw) == 0:
        raise AppError("empty_file", "فایل خالی است.", 422)
    if len(raw) > max_bytes:
        raise AppError("file_too_large", f"حجم تصویر بیش از {max_bytes // (1024 * 1024)} مگابایت است.", 413)
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise AppError("bad_file_type", "فقط تصویر JPG، PNG، WEBP یا HEIC پذیرفته می‌شود.", 415)
        if img.width * img.height > MAX_PIXELS:
            raise AppError("image_too_large", "ابعاد تصویر بیش از حد مجاز است.", 413)
        img.load()
    except AppError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as e:
        raise AppError("bad_file_type", "فایل ارسالی تصویر معتبر نیست.", 415) from e

    taken = _exif_datetime(img)
    img = ImageOps.exif_transpose(img)  # honour camera rotation BEFORE stripping EXIF
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    out = io.BytesIO()
    img.save(out, "WEBP", quality=84, method=4)  # re-encode → no EXIF/GPS leaks into storage
    th = img.copy()
    th.thumbnail((THUMB_EDGE, THUMB_EDGE))
    tout = io.BytesIO()
    th.save(tout, "WEBP", quality=78)
    return ProcessedImage(out.getvalue(), tout.getvalue(), "image/webp", img.width, img.height,
                          hashlib.sha256(raw).hexdigest(), taken)
