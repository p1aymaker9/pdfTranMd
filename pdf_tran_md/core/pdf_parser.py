from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

import fitz

from pdf_tran_md.core.text import normalize_whitespace, split_text_by_paragraphs
from pdf_tran_md.models import Chunk, Section, TocItem


def build_footnote_skeletons(
    doc: fitz.Document, sections: List[Section]
) -> Tuple[dict[str, list[str]], Dict[int, List[int]], Dict[int, float]]:
    page_to_notes: dict[int, List[str]] = {}
    page_cutoffs: Dict[int, float] = {}
    for section in sections:
        for pno in range(section.start_page - 1, section.end_page):
            page = doc.load_page(pno)
            blocks = page.get_text("blocks")
            page_height = page.rect.height
            cutoff = page_height * 0.82
            page_cutoffs[pno + 1] = cutoff
            note_lines: List[str] = []
            for block in blocks:
                if len(block) < 7:
                    continue
                y0 = block[1]
                text = (block[4] or "").strip()
                if y0 < cutoff or not text:
                    continue
                note_lines.append(text)
            if note_lines:
                page_to_notes[pno + 1] = note_lines

    skeletons: dict[str, list[str]] = {}
    footnote_numbers: Dict[int, List[int]] = {}
    for page_no, notes in page_to_notes.items():
        items: List[Tuple[Optional[int], str]] = []
        for note in notes:
            for line in note.split("\n"):
                line = line.strip()
                if line:
                    items.append(_parse_footnote_line(line))
        if not items:
            continue

        resolved: List[str] = []
        numbers: List[int] = []
        fallback = 1
        for number, content in items:
            note_no = number or fallback
            fallback = note_no + 1
            numbers.append(note_no)
            resolved.append(f"[[FN{note_no}]] {content}")
        skeletons[str(page_no)] = resolved
        footnote_numbers[page_no] = numbers

    return skeletons, footnote_numbers, page_cutoffs


def _parse_footnote_line(line: str) -> Tuple[Optional[int], str]:
    patterns = [
        r"^\[(\d+)\]\s*",
        r"^（\s*(\d+)\s*）\s*",
        r"^\(\s*(\d+)\s*\)\s*",
        r"^(\d+)[\).、]\s*",
    ]
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            number = int(match.group(1))
            content = line[match.end():].strip()
            return number, content
    return None, line


def _page_text_above_cutoff(page: fitz.Page, cutoff: float) -> str:
    blocks = page.get_text("blocks")
    rows: List[Tuple[float, float, str]] = []
    for block in blocks:
        if len(block) < 7:
            continue
        x0, y0, _, _, text = block[:5]
        if y0 >= cutoff:
            continue
        cleaned = (text or "").strip()
        if cleaned:
            rows.append((y0, x0, cleaned))
    rows.sort(key=lambda item: (item[0], item[1]))
    return "\n".join(item[2] for item in rows)


def _insert_footnote_anchors(text: str, numbers: List[int]) -> str:
    for number in numbers:
        for pattern in (rf"\[{number}\]", rf"（{number}）", rf"\({number}\)"):
            if re.search(pattern, text):
                text = re.sub(pattern, f"[[FN{number}]]", text, count=1)
                break
    return text


def load_toc(doc: fitz.Document) -> List[TocItem]:
    raw_toc = doc.get_toc(simple=True) or []
    toc_items: List[TocItem] = []
    for item in raw_toc:
        if len(item) >= 3 and isinstance(item[2], int) and item[2] >= 1:
            toc_items.append(TocItem(level=item[0], title=str(item[1]).strip(), page=item[2]))
    return toc_items


def build_sections_from_toc(doc: fitz.Document, toc_items: List[TocItem]) -> List[Section]:
    if not toc_items:
        return []

    sections: List[Section] = []
    for index, item in enumerate(toc_items):
        end_page = doc.page_count
        for next_item in toc_items[index + 1 :]:
            if next_item.level <= item.level:
                end_page = next_item.page - 1
                break
        end_page = max(item.page, end_page)
        sections.append(
            Section(
                index=index,
                level=item.level,
                title=item.title,
                start_page=item.page,
                end_page=end_page,
            )
        )
    return sections


def build_full_document_section(doc: fitz.Document) -> Section:
    return Section(index=0, level=1, title="全文", start_page=1, end_page=doc.page_count)


def get_pdf_text(
    doc: fitz.Document,
    start_page: int,
    end_page: int,
    page_markers: Optional[Set[int]] = None,
    page_footnote_numbers: Optional[Dict[int, List[int]]] = None,
    page_cutoffs: Optional[Dict[int, float]] = None,
) -> str:
    texts = []
    for pno in range(start_page - 1, end_page):
        page_no = pno + 1
        page = doc.load_page(pno)
        cutoff = page_cutoffs.get(page_no) if page_cutoffs else None
        page_text = _page_text_above_cutoff(page, cutoff) if cutoff else page.get_text("text")
        if page_footnote_numbers and page_no in page_footnote_numbers:
            page_text = _insert_footnote_anchors(page_text, page_footnote_numbers[page_no])
        texts.append(page_text)
        if page_markers and page_no in page_markers:
            texts.append(f"[[PAGE:{page_no}]]")
    return normalize_whitespace("\n\n".join(texts))


def build_chunks_for_sections(
    doc: fitz.Document,
    sections: List[Section],
    max_chars: int = 5000,
    page_markers: Optional[Set[int]] = None,
    page_footnote_numbers: Optional[Dict[int, List[int]]] = None,
    page_cutoffs: Optional[Dict[int, float]] = None,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_id = 0

    for section in sections:
        text = get_pdf_text(
            doc,
            section.start_page,
            section.end_page,
            page_markers=page_markers,
            page_footnote_numbers=page_footnote_numbers,
            page_cutoffs=page_cutoffs,
        )
        if not text.strip():
            continue

        for piece in split_text_by_paragraphs(text, max_chars=max_chars):
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    section_index=section.index,
                    section_title=section.title,
                    section_level=section.level,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    source_text=piece,
                )
            )
            chunk_id += 1

    return chunks
