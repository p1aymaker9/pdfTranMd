from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


STATE_VERSION = 9


@dataclass
class TocItem:
    level: int
    title: str
    page: int


@dataclass
class Section:
    index: int
    level: int
    title: str
    start_page: int
    end_page: int


@dataclass
class Chunk:
    chunk_id: int
    section_index: int
    section_title: str
    section_level: int
    start_page: int
    end_page: int
    source_text: str


@dataclass
class TranslationSettings:
    api_base: str
    api_key: str
    model: str
    target_language: str = "中文"
    api_keys: List[str] = field(default_factory=list)
    enhance_markdown: bool = True
    temperature: float = 0.0
    max_concurrency: int = 2
    min_request_interval: float = 0.8
    timeout: int = 180


@dataclass
class ProviderProfile:
    name: str
    api_base: str
    api_key: str
    model: str
    target_language: str = "中文"
    api_keys: List[str] = field(default_factory=list)
    temperature: float = 0.0
    max_concurrency: int = 2
    min_request_interval: float = 0.8
    timeout: int = 180

    def to_settings(self) -> TranslationSettings:
        return TranslationSettings(
            api_base=self.api_base,
            api_key=self.api_key,
            model=self.model,
            target_language=self.target_language,
            api_keys=self.api_keys,
            temperature=self.temperature,
            max_concurrency=self.max_concurrency,
            min_request_interval=self.min_request_interval,
            timeout=self.timeout,
        )


@dataclass
class AppConfig:
    profiles: List[ProviderProfile] = field(default_factory=list)
    selected_profile: str = ""
    last_pdf_path: str = ""
    last_output_path: str = ""
    last_pdf_export_path: str = ""
    last_target_language: str = "中文"
    export_pdf: bool = False
    enhance_markdown: bool = True
    dark_mode: bool = False


@dataclass
class TranslationState:
    version: int
    pdf_path: str
    output_path: str
    settings: Dict[str, Any]
    translate_mode: str
    selected_section_indices: List[int]
    chunks: List[Dict[str, Any]]
    footnote_skeletons: Dict[str, List[str]]
    completed_translations: Dict[str, str]
    written_chunk_ids: List[int]
    export_pdf: bool = False
    pdf_output_path: str = ""
    markdown_header_written: bool = False
    started_at: float = 0.0


@dataclass
class JobConfig:
    pdf_path: str
    output_path: str
    translate_mode: str
    selected_sections: List[Dict[str, Any]]
    settings: Dict[str, Any]
    export_pdf: bool = False
    pdf_output_path: str = ""


def to_dict_list(items: List[Any]) -> List[Dict[str, Any]]:
    return [asdict(item) for item in items]
