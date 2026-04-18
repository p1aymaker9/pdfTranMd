# PDF 翻译到 Markdown

一个桌面 GUI 工具：将 PDF 内容翻译为 Markdown，并提供预览与导出 PDF 能力。

## 特性
- PDF 解析与分段翻译
- Markdown 预览（含结构增强选项）
- 支持断点续译
- 可导出翻译后的 PDF

## 环境与依赖
- Python 3
- 依赖安装

```bash
pip install pymupdf requests Markdown
```

## 使用方式
启动应用：

```bash
python3 app.py
```

语法检查：

```bash
python3 -m py_compile app.py
```

## 桌面应用打包
仓库包含 GitHub Actions 配置，可在没有 Mac 或 Windows 设备的情况下用 GitHub runner 打包。

触发方式：
- 在 GitHub 仓库页面进入 `Actions` -> `Build Desktop Apps` -> `Run workflow`
- 或推送 `v*` 形式的 tag，例如 `v0.1.0`

打包产物会上传为 artifact，并在 tag 构建时发布到 GitHub Releases：
- `PDFTranMd-macos-arm64.zip`：Apple Silicon arm64，适用于 M2 及之后的 Mac
- `PDFTranMd-windows-x64.zip`：Windows x64

本地 macOS 打包命令：

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --clean --noconfirm PDFTranMd.spec
```

Windows 打包需在 Windows 环境中运行：

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --clean --noconfirm PDFTranMd.windows.spec
```

`PDFTranMd.spec` 和 `PDFTranMd.windows.spec` 已排除当前未使用的 Qt 模块，以减少 PySide6 打包体积。

## 项目结构
- `app.py`：应用入口
- `pdf_tran_md/`：核心逻辑与 UI
- 运行产物：
  - `*_translated.md`
  - `*.translate_state.json`

## 结构增强说明
启用“结构增强”后，会尝试保留更清晰的 Markdown 结构（如脚注、标题等）。  
该行为以本地解析结果为主，模型仅做翻译与最小必要格式化。

## 预览与导出
预览使用 Markdown 渲染输出 HTML。  
导出 PDF 使用渲染后的 HTML 生成。

## 注意事项
- 不要在代码中硬编码 API Key
- 翻译输出和断点文件属于本地生成产物

## 许可证
尚未指定。需要发布时请补充 LICENSE。
