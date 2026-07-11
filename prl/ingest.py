from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from .models import BinaryAsset


class UploadError(ValueError):
    pass


MAX_ARCHIVE_ENTRIES = 1000
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250
MAX_SESSION_INPUT_BYTES = 300 * 1024 * 1024


def _kind_from_name(name: str) -> str | None:
    lower = name.lower()
    if lower.endswith(".roi"):
        return "roi"
    if lower.endswith((".dcm", ".dicom")):
        return "dicom"
    return None


def _asset(name: str, data: bytes, kind: str, source_name: str, member: str | None = None) -> BinaryAsset:
    digest = hashlib.sha256()
    digest.update(name.encode("utf-8", errors="replace"))
    digest.update(data)
    return BinaryAsset(
        uid=digest.hexdigest()[:16],
        name=name,
        data=data,
        kind=kind,
        source_name=source_name,
        archive_member=member,
    )


def _read_zip(source_name: str, payload: bytes) -> tuple[list[BinaryAsset], list[str]]:
    assets: list[BinaryAsset] = []
    notices: list[str] = []
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except Exception as exc:
        raise UploadError(f"{source_name}: ZIP archive could not be opened: {exc}") from exc
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            raise UploadError(
                f"{source_name}: archive contains {len(infos)} files; the limit is {MAX_ARCHIVE_ENTRIES}."
            )
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise UploadError(f"{source_name}: unsafe ZIP member path: {info.filename}")
            if info.flag_bits & 0x1:
                raise UploadError(f"{source_name}: encrypted ZIP members are not supported.")
            if info.file_size > MAX_MEMBER_BYTES:
                raise UploadError(f"{source_name}: {info.filename} exceeds the per-file limit.")
            total += info.file_size
            if total > MAX_ARCHIVE_BYTES:
                raise UploadError(f"{source_name}: uncompressed archive exceeds 256 MB.")
            if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise UploadError(f"{source_name}: suspicious compression ratio for {info.filename}.")
            kind = _kind_from_name(info.filename)
            if kind is None:
                continue
            data = archive.read(info)
            display_name = info.filename.replace("\\", "/")
            assets.append(_asset(display_name, data, kind, source_name, info.filename))
        ignored = len(infos) - len(assets)
        if ignored:
            notices.append(f"{source_name}: ignored {ignored} non-ROI/DICOM archive file(s).")
    return assets, notices


def process_uploads(files: list[tuple[str, bytes]]) -> tuple[list[BinaryAsset], list[str]]:
    assets: list[BinaryAsset] = []
    notices: list[str] = []
    uploaded_total = 0
    accepted_total = 0
    for name, data in files:
        uploaded_total += len(data)
        if uploaded_total > MAX_SESSION_INPUT_BYTES:
            raise UploadError("Combined uploaded files exceed the 300 MB session limit.")
        if not data:
            notices.append(f"{name}: empty file ignored.")
            continue
        if name.lower().endswith(".zip"):
            nested, nested_notices = _read_zip(name, data)
            accepted_total += sum(len(asset.data) for asset in nested)
            if accepted_total > MAX_SESSION_INPUT_BYTES:
                raise UploadError(
                    "Combined uncompressed ROI/DICOM data exceed the 300 MB session limit."
                )
            assets.extend(nested)
            notices.extend(nested_notices)
            continue
        kind = _kind_from_name(name)
        if kind is None:
            notices.append(f"{name}: unsupported file type ignored.")
            continue
        accepted_total += len(data)
        if accepted_total > MAX_SESSION_INPUT_BYTES:
            raise UploadError("Combined ROI/DICOM data exceed the 300 MB session limit.")
        assets.append(_asset(name, data, kind, name))
    deduped: dict[str, BinaryAsset] = {}
    for asset in assets:
        if asset.uid in deduped:
            notices.append(f"{asset.name}: exact duplicate ignored.")
        else:
            deduped[asset.uid] = asset
    return list(deduped.values()), notices
