# PDFTranMd

一个桌面 GUI 工具，用于将 PDF 内容翻译为 Markdown，并提供 Markdown 预览、断点续译和导出 PDF 能力。

## 特性
- 解析 PDF 目录，并支持翻译全文或仅翻译所选章节
- 将长文档拆分为段落块，便于分批调用 OpenAI 兼容接口
- 支持断点续译，异常中断后可继续任务
- 提供 Markdown 预览和结构增强选项
- 可导出翻译后的 Markdown 与 PDF

## 环境与依赖
- Python 3.12 推荐
- PySide6、PyMuPDF、requests、Markdown

```bash
pip install -r requirements.txt
```

## 本地运行
启动应用：

```bash
python3 app.py
```

语法检查：

```bash
python3 -m py_compile app.py
```

## 下载发布版
用户可以在 GitHub Releases 下载已打包好的桌面程序：

https://github.com/p1aymaker9/pdfTranMd/releases

当前自动发布的产物：
- `PDFTranMd-macos-arm64.zip`：Apple Silicon arm64，适用于 M2 及之后的 Mac
- `PDFTranMd-windows-x64.zip`：Windows x64

macOS 版本未做 Apple Developer ID 签名和 notarization 时，系统可能提示无法验证开发者。此时可右键应用并选择“打开”。

## 桌面应用打包
仓库包含 GitHub Actions 配置，可在没有 Mac 或 Windows 设备的情况下用 GitHub runner 打包。

触发方式：
- 在 GitHub 仓库页面进入 `Actions` -> `Build Desktop Apps` -> `Run workflow`
- 或推送 `v*` 形式的 tag，例如：

```bash
git tag v0.1.4
git push origin v0.1.4
```

tag 构建成功后，CI 会创建对应版本的 GitHub Release，并上传 macOS 与 Windows 两个 zip。Actions artifact 也会保留一份用于调试。

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
- `PDFTranMd.spec`：macOS Apple Silicon PyInstaller 配置
- `PDFTranMd.windows.spec`：Windows x64 PyInstaller 配置
- `.github/workflows/build-macos.yml`：桌面应用自动打包与 Release 发布流程
- 运行产物：
  - `*_translated.md`
  - `*_translated.pdf`
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
- 打包产物依赖 PySide6 和 PyMuPDF，体积较大是正常现象

## 许可证
MIT License。详见 `LICENSE`。
