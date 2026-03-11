# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Single-entry GUI application for translating PDF content to Markdown.
- Runtime artifacts: output files like `*_translated.md` and checkpoint state files `*.translate_state.json` are generated next to the selected output path.
- No dedicated `src/` or `tests/` directories yet; keep new modules small and place them near `app.py` until the project is split.

## UI Notes
- 翻译范围在“翻译输入”区使用两个单选按钮（翻译全部 / 仅翻译所选章节）。
- “章节选择”列表已放大，适合显示更多目录项。
- “运行日志”支持折叠，默认占用较小高度。

## Build, Test, and Development Commands

- 虚拟环境已经使用pyenv配置好
 `pip install pymupdf requests`: install runtime dependencies used by `app.py` (`fitz` comes from `pymupdf`).
- `python3 app.py`: launch the desktop translator UI.
- `python3 -m py_compile app.py`: quick syntax validation before committing.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and descriptive snake_case names for functions/variables.
- Use `PascalCase` for classes (for example `PDFTranslatorApp`, `TranslatorEngine`) and dataclasses.
- Keep functions focused and side effects explicit (especially file writes and network calls).
- Preserve UTF-8 handling for user-visible text and generated Markdown.

## Testing Guidelines
- There is currently no automated test suite in this snapshot.
- For logic changes, add `pytest` tests under a new `tests/` folder using names like `test_split_text_by_paragraphs.py`.
- Minimum validation for UI-affecting changes:
  - Run `python3 app.py` and verify PDF loading, queue operations, and checkpoint resume.
  - Run `python3 -m py_compile app.py` to catch syntax regressions.

## Commit & Pull Request Guidelines
- Git history is not available in this workspace snapshot; use Conventional Commit style by default (`feat:`, `fix:`, `refactor:`, `docs:`).
- Keep commits focused (one behavior change per commit where possible).
- PRs should include:
  - What changed and why.
  - Manual test steps and results.
  - Screenshots/GIFs for UI changes.
  - Linked issue/task when applicable.

## Security & Configuration Tips
- Never hardcode API keys in source files.
- Treat generated translation/state files as local artifacts; avoid committing sensitive PDF-derived output.
