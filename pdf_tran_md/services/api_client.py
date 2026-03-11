from __future__ import annotations

import asyncio
import json
import threading
import traceback
from typing import List

import requests

from pdf_tran_md.core.text import cleanup_translated_markdown
from pdf_tran_md.models import TranslationSettings


class APIError(Exception):
    pass


class OpenAICompatibleClient:
    def __init__(self, settings: TranslationSettings):
        self.settings = settings
        self._key_lock = threading.Lock()
        self._key_index = 0

    def _available_keys(self) -> List[str]:
        keys = [key.strip() for key in self.settings.api_keys if key.strip()]
        if self.settings.api_key.strip() and self.settings.api_key.strip() not in keys:
            keys.insert(0, self.settings.api_key.strip())
        return keys

    def _next_api_key(self) -> str:
        keys = self._available_keys()
        if not keys:
            return self.settings.api_key.strip()
        with self._key_lock:
            key = keys[self._key_index % len(keys)]
            self._key_index += 1
        return key

    def _system_prompt(self) -> str:
        target_language = self.settings.target_language.strip() or "中文"
        structure_rules = (
            "3. 如果文本本身明显是标题，请输出简洁的 Markdown 标题；不要给普通段落随意加标题。\n"
            "4. 如果文本中出现脚注/注释条目，优先整理成 Markdown 脚注格式 `[^n]: ...`。\n"
        ) if self.settings.enhance_markdown else (
            "3. 尽量保持原文段落与行文结构，不要主动添加 Markdown 标题或脚注语法。\n"
            "4. 如果原文包含注释编号，仅保留其可读含义，不做额外结构改写。\n"
        )
        return (
            f"你是一个严谨的 PDF 学术翻译助手。请将用户提供的内容完整翻译为{target_language}，"
            "并直接输出适合写入 Markdown 文件的正文。\n"
            "要求：\n"
            "1. 忠实完整翻译，不得概括、删减、补写，不要回答分析过程。\n"
            "2. 保留段落边界、编号层级、列表、表格语义、引用关系和脚注标记。\n"
            "2.1 如果出现形如 [[PAGE:数字]] 或 [[FN数字]] 的标记，请原样保留，不翻译不改写。\n"
            f"{structure_rules}"
            "5. 公式、变量名、专有缩写、文献编号、页码引用和代码片段尽量保持原样。\n"
            "6. 不要输出 ```markdown 代码块包裹，不要添加前言、总结、译者说明。\n"
        )

    def _candidate_urls(self) -> List[str]:
        base = self.settings.api_base.strip().rstrip("/")
        candidates = []
        if base.endswith("/chat/completions"):
            candidates.append(base)
        else:
            candidates.append(base + "/chat/completions")
            if not base.endswith("/v1"):
                candidates.append(base + "/v1/chat/completions")

        seen = set()
        result = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
        return result

    def _translate_sync(self, text: str) -> str:
        payload = {
            "model": self.settings.model,
            "temperature": self.settings.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {"role": "user", "content": text},
            ],
        }
        api_key = self._next_api_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        errors = []
        for url in self._candidate_urls():
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.timeout,
                )
                if response.status_code != 200:
                    retry_after = response.headers.get("Retry-After")
                    detail = (
                        f"API 请求失败\n"
                        f"- URL: {url}\n"
                        f"- HTTP 状态码: {response.status_code}\n"
                        f"- Retry-After: {retry_after or 'n/a'}\n"
                        f"- 响应正文预览:\n{(response.text or '(empty response body)')[:3000]}"
                    )
                    if response.status_code == 429:
                        raise APIError(detail)
                    errors.append(detail)
                    continue

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    raise APIError(
                        "API 返回成功，但未找到 choices[0].message.content。\n"
                        f"URL: {url}\n"
                        f"响应 JSON 预览:\n{json.dumps(data, ensure_ascii=False)[:3000]}"
                    )
                return content.strip()
            except requests.exceptions.RequestException as exc:
                errors.append(
                    f"请求异常\n- URL: {url}\n- 异常类型: {type(exc).__name__}\n- 异常信息: {exc}"
                )
            except APIError:
                raise
            except Exception as exc:
                errors.append(
                    f"未知异常\n- URL: {url}\n- 异常类型: {type(exc).__name__}\n- 异常信息: {exc}\n"
                    f"- Traceback:\n{traceback.format_exc()}"
                )

        raise APIError(
            "所有候选 API 地址均请求失败。\n\n"
            + "已尝试 URL：\n"
            + "\n".join(self._candidate_urls())
            + "\n\n详细错误如下：\n"
            + ("\n" + "=" * 70 + "\n").join(errors)
        )

    async def translate(self, text: str, *, apply_cleanup: bool = True) -> str:
        result = await asyncio.to_thread(self._translate_sync, text)
        if apply_cleanup and self.settings.enhance_markdown:
            return cleanup_translated_markdown(result)
        return result
