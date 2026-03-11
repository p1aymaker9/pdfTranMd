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
