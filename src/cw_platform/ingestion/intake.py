from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class UnsupportedFormatError(Exception):
    pass


class RawDocument(BaseModel):
    filename: str
    content: bytes
    format: Literal["pdf"]


def intake(filename: str, content: bytes) -> RawDocument:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix != "pdf":
        raise UnsupportedFormatError(
            f"Unsupported file extension '.{suffix}': only PDF is supported in this release."
        )
    return RawDocument(filename=filename, content=content, format="pdf")
