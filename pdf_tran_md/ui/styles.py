LIGHT_APP_QSS = """
QWidget {
    background: #f5f7fb;
    color: #18212f;
    font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei";
    font-size: 14px;
}
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef3fb, stop:1 #f8fafc);
}
QGroupBox {
    border: 1px solid #dbe4f0;
    border-radius: 18px;
    margin-top: 14px;
    padding-top: 14px;
    background: rgba(255, 255, 255, 0.92);
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
}
QLineEdit, QTextEdit, QListWidget, QListView, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextBrowser {
    border: 1px solid #d7e0ec;
    border-radius: 12px;
    padding: 8px 10px;
    background: #ffffff;
    selection-background-color: #2c6bed;
}
QPushButton {
    background: #18212f;
    color: white;
    border: none;
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: #274061;
}
QPushButton[variant="secondary"] {
    background: #e8eef7;
    color: #18212f;
}
QPushButton[variant="secondary"]:hover {
    background: #dde7f4;
}
QProgressBar {
    border: none;
    border-radius: 9px;
    background: #e4ebf5;
    min-height: 12px;
}
QProgressBar::chunk {
    border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e4fd4, stop:1 #43a4ff);
}
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    background: #e7edf7;
    padding: 8px 14px;
    margin-right: 6px;
    border-radius: 10px;
}
QTabBar::tab:selected {
    background: #18212f;
    color: white;
}
QCheckBox {
    spacing: 8px;
}
"""

DARK_APP_QSS = """
QWidget {
    background: #101620;
    color: #e6edf7;
    font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei";
    font-size: 14px;
}
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0c121b, stop:1 #151e2b);
}
QGroupBox {
    border: 1px solid #2b3a50;
    border-radius: 18px;
    margin-top: 14px;
    padding-top: 14px;
    background: rgba(23, 32, 46, 0.96);
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
}
QLineEdit, QTextEdit, QListWidget, QListView, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextBrowser {
    border: 1px solid #31435b;
    border-radius: 12px;
    padding: 8px 10px;
    background: #172131;
    color: #edf3ff;
    selection-background-color: #5d96ff;
}
QPushButton {
    background: #d8e4f7;
    color: #0f1722;
    border: none;
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: #edf4ff;
}
QPushButton[variant="secondary"] {
    background: #243246;
    color: #e6edf7;
}
QPushButton[variant="secondary"]:hover {
    background: #30435c;
}
QProgressBar {
    border: none;
    border-radius: 9px;
    background: #253246;
    min-height: 12px;
}
QProgressBar::chunk {
    border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8dff, stop:1 #7bd1ff);
}
QTabWidget::pane {
    border: none;
}
QTabBar::tab {
    background: #223044;
    color: #cdd7e6;
    padding: 8px 14px;
    margin-right: 6px;
    border-radius: 10px;
}
QTabBar::tab:selected {
    background: #d7e5f8;
    color: #111b28;
}
QCheckBox {
    spacing: 8px;
}
"""

LIGHT_MARKDOWN_CSS = """
body {
    font-family: "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 36px 80px;
    color: #1a2330;
    background:
        radial-gradient(circle at top right, rgba(79, 161, 255, 0.14), transparent 30%),
        linear-gradient(180deg, #fbfcff 0%, #f4f7fb 100%);
    line-height: 1.8;
}
h1, h2, h3, h4, h5, h6 {
    font-family: "Noto Sans CJK SC", "PingFang SC", sans-serif;
    color: #112035;
    margin-top: 1.8em;
    margin-bottom: 0.7em;
    letter-spacing: 0.02em;
}
h1 {
    font-size: 2em;
    border-bottom: 2px solid #d9e4f2;
    padding-bottom: 0.3em;
}
h2 {
    font-size: 1.5em;
    border-left: 4px solid #2c6bed;
    padding-left: 0.6em;
}
p, li {
    font-size: 16px;
}
code {
    background: #edf3ff;
    color: #123470;
    padding: 0.15em 0.35em;
    border-radius: 6px;
}
pre {
    background: #152033;
    color: #edf3ff;
    padding: 16px;
    border-radius: 16px;
    overflow-x: auto;
}
blockquote {
    margin-left: 0;
    padding: 0.6em 1em;
    border-left: 4px solid #9ab5dd;
    background: rgba(255, 255, 255, 0.65);
}
hr {
    border: none;
    border-top: 1px solid #d4dfef;
    margin: 2em 0;
}
a {
    color: #1e56da;
}
"""

DARK_MARKDOWN_CSS = """
body {
    font-family: "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 36px 80px;
    color: #e6edf7;
    background:
        radial-gradient(circle at top right, rgba(112, 160, 255, 0.16), transparent 32%),
        linear-gradient(180deg, #0f1722 0%, #121b28 100%);
    line-height: 1.8;
}
h1, h2, h3, h4, h5, h6 {
    font-family: "Noto Sans CJK SC", "PingFang SC", sans-serif;
    color: #f2f7ff;
    margin-top: 1.8em;
    margin-bottom: 0.7em;
    letter-spacing: 0.02em;
}
h1 {
    font-size: 2em;
    border-bottom: 2px solid #32445f;
    padding-bottom: 0.3em;
}
h2 {
    font-size: 1.5em;
    border-left: 4px solid #74a8ff;
    padding-left: 0.6em;
}
p, li {
    font-size: 16px;
}
code {
    background: #1d2a3b;
    color: #bad4ff;
    padding: 0.15em 0.35em;
    border-radius: 6px;
}
pre {
    background: #0b111a;
    color: #edf3ff;
    padding: 16px;
    border-radius: 16px;
    overflow-x: auto;
}
blockquote {
    margin-left: 0;
    padding: 0.6em 1em;
    border-left: 4px solid #5f7faa;
    background: rgba(255, 255, 255, 0.04);
}
hr {
    border: none;
    border-top: 1px solid #33465f;
    margin: 2em 0;
}
a {
    color: #8cb4ff;
}
"""

APP_QSS = LIGHT_APP_QSS
MARKDOWN_CSS = LIGHT_MARKDOWN_CSS


def get_app_qss(dark_mode: bool) -> str:
    return DARK_APP_QSS if dark_mode else LIGHT_APP_QSS


def get_markdown_css(dark_mode: bool) -> str:
    return DARK_MARKDOWN_CSS if dark_mode else LIGHT_MARKDOWN_CSS
