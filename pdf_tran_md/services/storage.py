from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from pdf_tran_md.models import AppConfig, ProviderProfile, TranslationState


def state_file_path(output_md_path: str) -> str:
    return output_md_path + ".translate_state.json"


def ensure_utf8_write(path: str, text: str, mode: str = "a") -> None:
    with open(path, mode, encoding="utf-8") as file:
        file.write(text)


def _normalize_profile(raw: dict) -> ProviderProfile:
    item = dict(raw)
    api_keys = item.get("api_keys") or []
    if isinstance(api_keys, str):
        api_keys = [key.strip() for key in api_keys.splitlines() if key.strip()]
    item["api_keys"] = api_keys
    item.setdefault("target_language", "中文")
    return ProviderProfile(**item)


class StateStore:
    def save(self, state: TranslationState) -> None:
        with open(state_file_path(state.output_path), "w", encoding="utf-8") as file:
            json.dump(asdict(state), file, ensure_ascii=False, indent=2)

    def load(self, output_path: str) -> TranslationState:
        with open(state_file_path(output_path), "r", encoding="utf-8") as file:
            raw = json.load(file)
        raw.setdefault("export_pdf", False)
        raw.setdefault("pdf_output_path", "")
        raw.setdefault("footnote_skeletons", {})
        raw.setdefault("settings", {})
        raw["settings"].setdefault("target_language", "中文")
        raw["settings"].setdefault("enhance_markdown", True)
        api_keys = raw["settings"].get("api_keys") or []
        if isinstance(api_keys, str):
            api_keys = [key.strip() for key in api_keys.splitlines() if key.strip()]
        raw["settings"]["api_keys"] = api_keys
        return TranslationState(**raw)

    def clear(self, output_path: str) -> None:
        path = state_file_path(output_path)
        if os.path.exists(path):
            os.remove(path)


class ConfigStore:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path.home() / ".pdf_tran_md_config.json")

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()

        with open(self.config_path, "r", encoding="utf-8") as file:
            raw = json.load(file)

        profiles = [_normalize_profile(item) for item in raw.get("profiles", [])]
        return AppConfig(
            profiles=profiles,
            selected_profile=raw.get("selected_profile", ""),
            last_pdf_path=raw.get("last_pdf_path", ""),
            last_output_path=raw.get("last_output_path", ""),
            last_pdf_export_path=raw.get("last_pdf_export_path", ""),
            last_target_language=raw.get("last_target_language", "中文"),
            export_pdf=raw.get("export_pdf", False),
            enhance_markdown=raw.get("enhance_markdown", True),
            dark_mode=raw.get("dark_mode", False),
        )

    def save(self, config: AppConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "profiles": [asdict(profile) for profile in config.profiles],
                    "selected_profile": config.selected_profile,
                    "last_pdf_path": config.last_pdf_path,
                    "last_output_path": config.last_output_path,
                    "last_pdf_export_path": config.last_pdf_export_path,
                    "last_target_language": config.last_target_language,
                    "export_pdf": config.export_pdf,
                    "enhance_markdown": config.enhance_markdown,
                    "dark_mode": config.dark_mode,
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

        try:
            os.chmod(self.config_path, 0o600)
        except OSError:
            pass
