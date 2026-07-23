"""
pdf_extract.py
Extracts raw text plus layout signals from a resume PDF using pdfplumber.
Layout signals (images, multi-column) power the ATS-safety dimension, since
those checks cannot be inferred from plain text alone.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import io

import pdfplumber


@dataclass
class ExtractedResume:
    raw_text: str
    page_count: int
    has_images: bool
    is_multi_column: bool
    line_count: int
    lines: List[str] = field(default_factory=list)


def _detect_multi_column(words) -> bool:
    """Heuristic: a two-column layout shows two dense clusters of word start-x
    with a clear empty gutter between them, and many rows populated on both sides."""
    if not words:
        return False
    xs = sorted(w["x0"] for w in words)
    page_left, page_right = xs[0], max(w["x1"] for w in words)
    width = page_right - page_left
    if width <= 0:
        return False
    mid = page_left + width / 2
    # words that clearly start in the right half (past 55% of the page)
    right_start = page_left + width * 0.55
    right_words = [w for w in words if w["x0"] >= right_start]
    left_words = [w for w in words if w["x0"] < mid]
    if not left_words or not right_words:
        return False
    right_ratio = len(right_words) / len(words)
    # Group by row (rounded top) and count rows that have BOTH a left and right block
    rows: dict = {}
    for w in words:
        key = round(w["top"] / 6)
        rows.setdefault(key, []).append(w)
    dual_rows = 0
    for r in rows.values():
        has_left = any(w["x0"] < mid for w in r)
        has_right = any(w["x0"] >= right_start for w in r)
        if has_left and has_right:
            dual_rows += 1
    dual_ratio = dual_rows / max(len(rows), 1)
    return right_ratio > 0.18 and dual_ratio > 0.35


def extract_resume(data: bytes) -> ExtractedResume:
    text_parts: List[str] = []
    has_images = False
    multi_col = False
    page_count = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            if page.images:
                has_images = True
            words = page.extract_words(use_text_flow=False)
            if _detect_multi_column(words):
                multi_col = True
            t = page.extract_text() or ""
            text_parts.append(t)
    raw = "\n".join(text_parts)
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    return ExtractedResume(
        raw_text=raw,
        page_count=page_count,
        has_images=has_images,
        is_multi_column=multi_col,
        line_count=len(lines),
        lines=lines,
    )


def extract_from_text(raw: str) -> ExtractedResume:
    """Fallback path when only pasted text is available (no layout signals)."""
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    return ExtractedResume(
        raw_text=raw, page_count=1, has_images=False,
        is_multi_column=False, line_count=len(lines), lines=lines,
    )
