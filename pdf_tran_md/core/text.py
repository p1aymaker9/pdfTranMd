from __future__ import annotations

import re
from typing import List


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def cleanup_translated_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"(?m)^[ \t]+", "", text)
    text = re.sub(r"(?m)^\[(\d+)\][ \t]+", lambda m: f"[^{m.group(1)}]: ", text)
    text = re.sub(r"(?m)^（?注(\d+)）?[：:]\s*", lambda m: f"[^{m.group(1)}]: ", text)
    text = re.sub(r"(?m)^(第[一二三四五六七八九十百零0-9]+[章节部分篇]\s+.+)$", r"## \1", text)
    text = re.sub(r"(?m)^(附录[A-Z0-9一二三四五六七八九十]+[^\n]*)$", r"## \1", text)
    text = re.sub(r"\[\[FN(\d+)\]\]\s*:", lambda m: f"[^{m.group(1)}]:", text)
    text = re.sub(r"\[\[FN(\d+)\]\]", lambda m: f"[^{m.group(1)}]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_inline_ordered_lists_for_preview(text: str) -> str:
    lines = text.split("\n")
    out: List[str] = []
    list_pattern = re.compile(r"\b(\d+)\.\s")
    for line in lines:
        matches = list(list_pattern.finditer(line))
        if len(matches) < 2:
            out.append(line)
            continue
        line = re.sub(r"\s+(?=\d+\.\s)", "\n", line)
        out.extend(line.split("\n"))

    return "\n".join(out)


def split_long_paragraph(text: str, max_chars: int = 5000) -> List[str]:
    pieces = re.split(r"(?<=[。！？.!?；;:])\s+|\n", text)
    out: List[str] = []
    current = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue

        if len(piece) > max_chars:
            if current:
                out.append(current.strip())
                current = ""
            for i in range(0, len(piece), max_chars):
                out.append(piece[i : i + max_chars].strip())
            continue

        candidate = (current + " " + piece).strip() if current else piece
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                out.append(current.strip())
            current = piece

    if current:
        out.append(current.strip())

    return out


def split_text_by_paragraphs(text: str, max_chars: int = 5000) -> List[str]:
    text = normalize_whitespace(text)
    if not text:
        return []

    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current: List[str] = []

    def current_len(parts: List[str]) -> int:
        return sum(len(p) for p in parts) + max(0, 2 * (len(parts) - 1))

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > max_chars:
            if current:
                chunks.append("\n\n".join(current).strip())
                current = []
            chunks.extend(split_long_paragraph(para, max_chars=max_chars))
            continue

        if current_len(current + [para]) <= max_chars:
            current.append(para)
        else:
            if current:
                chunks.append("\n\n".join(current).strip())
            current = [para]

    if current:
        chunks.append("\n\n".join(current).strip())

    return [chunk for chunk in chunks if chunk.strip()]
