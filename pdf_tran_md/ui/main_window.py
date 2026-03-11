from __future__ import annotations

import asyncio
import os
import traceback
from dataclasses import asdict
from typing import List, Optional

import fitz
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
    QRadioButton,
    QSizePolicy,
)

from pdf_tran_md import APP_NAME
from pdf_tran_md.core.pdf_parser import build_full_document_section, build_sections_from_toc, load_toc
from pdf_tran_md.models import JobConfig, ProviderProfile, Section, TranslationSettings
from pdf_tran_md.services.exporter import load_markdown_html
from pdf_tran_md.services.storage import ConfigStore, StateStore, state_file_path
from pdf_tran_md.services.translation_runner import TranslationRunner, format_seconds
from pdf_tran_md.ui.styles import get_app_qss


class WorkerThread(QThread):
    log_signal = Signal(str)
    status_signal = Signal(str)
    progress_signal = Signal(int, int, float, float)
    finished_signal = Signal(bool, str)

    def __init__(self, coroutine_factory):
        super().__init__()
        self.coroutine_factory = coroutine_factory

    def run(self) -> None:
        try:
            asyncio.run(self.coroutine_factory())
            self.finished_signal.emit(True, "")
        except Exception as exc:
            self.finished_signal.emit(False, f"{exc}\n\n{traceback.format_exc()}")


class PDFTranslatorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(980, 760)

        self.config_store = ConfigStore()
        self.state_store = StateStore()
        self.config = self.config_store.load()

        self.doc: Optional[fitz.Document] = None
        self.sections: List[Section] = []
        self.job_queue: List[JobConfig] = []
        self.extra_api_keys: List[str] = []
        self.runner = TranslationRunner(state_store=self.state_store)
        self.worker_thread: Optional[WorkerThread] = None
        self.preview_markdown_path = ""
        self.preview_follows_output = True

        self._build_ui()
        self.apply_theme()
        self._load_config_to_ui()
        self.on_mode_changed()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        self.setCentralWidget(central)
        layout.addWidget(self._build_top_tabs())

    def _build_top_tabs(self) -> QTabWidget:
        self.top_tabs = QTabWidget()
        self.top_tabs.addTab(self._build_translation_tab(), "翻译任务")
        self.top_tabs.addTab(self._build_settings_tab(), "API 配置")
        self.top_tabs.addTab(self._build_preview_tab(), "Markdown 预览")
        return self.top_tabs

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.addWidget(self._build_profile_group())
        layout.addWidget(self._build_appearance_group())
        layout.addStretch(1)
        return page

    def _build_translation_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(self._build_status_group(), 1)
        top_row.addWidget(self._build_task_group(), 2)
        top_row.addWidget(self._build_export_group(), 2)
        left_col.addLayout(top_row)
        left_col.addWidget(self._build_section_group(), 2)
        left_col.addWidget(self._build_control_group())

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.addWidget(self._build_queue_group(), 1)
        right_col.addWidget(self._build_log_group(), 1)

        layout.addLayout(left_col, 3)
        layout.addLayout(right_col, 2)
        return page

    def _build_preview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.preview_path_label = QLabel("未选择 Markdown 文件")
        choose_btn = QPushButton("选择 Markdown")
        choose_btn.clicked.connect(self.choose_markdown_preview)
        self._mark_secondary(choose_btn)
        refresh_btn = QPushButton("刷新预览")
        refresh_btn.clicked.connect(self.refresh_preview_if_possible)
        self._mark_secondary(refresh_btn)
        toolbar.addWidget(self.preview_path_label, 1)
        toolbar.addWidget(choose_btn)
        toolbar.addWidget(refresh_btn)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setHtml("<html><body><p>暂无 Markdown 预览。</p></body></html>")

        layout.addLayout(toolbar)
        layout.addWidget(self.preview_browser, 1)
        return page

    def _build_status_group(self) -> QGroupBox:
        group = QGroupBox("运行状态")
        layout = QVBoxLayout(group)
        self.status_label = QLabel("就绪")
        self.progress_label = QLabel("0 / 0 (0.0%)")
        self.summary_label = QLabel("尚未读取 PDF")
        self.queue_label = QLabel("队列：0 个任务")
        self.progress_bar = QProgressBar()

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.queue_label)
        layout.addWidget(self.progress_bar)
        return group

    def _build_task_group(self) -> QGroupBox:
        group = QGroupBox("翻译输入")
        layout = QGridLayout(group)

        self.pdf_path_edit = QLineEdit()
        self.mode_all_radio = QRadioButton("翻译全部")
        self.mode_selected_radio = QRadioButton("仅翻译所选章节")
        self.mode_all_radio.setChecked(True)
        self.mode_all_radio.toggled.connect(self.on_mode_changed)
        self.mode_selected_radio.toggled.connect(self.on_mode_changed)
        self.target_language_combo = QComboBox()
        self.target_language_combo.setEditable(True)
        self.target_language_combo.addItems(["中文", "English", "日本語", "한국어", "Deutsch", "Français"])
        self.target_language_combo.currentTextChanged.connect(self.persist_session_paths)
        self.enhance_markdown_checkbox = QCheckBox("结构增强")
        self.enhance_markdown_checkbox.setChecked(True)
        self.enhance_markdown_checkbox.setToolTip("尝试把明显的章节标题和脚注整理成 Markdown 结构。")
        self.enhance_markdown_checkbox.toggled.connect(self.persist_session_paths)

        pdf_btn = QPushButton("选择 PDF")
        pdf_btn.clicked.connect(self.choose_pdf)

        layout.addWidget(QLabel("PDF 文件"), 0, 0)
        layout.addWidget(self.pdf_path_edit, 0, 1)
        layout.addWidget(pdf_btn, 0, 2)
        layout.addWidget(QLabel("翻译范围"), 1, 0)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.mode_all_radio)
        mode_row.addWidget(self.mode_selected_radio)
        mode_row.addStretch(1)
        layout.addLayout(mode_row, 1, 1, 1, 2)
        layout.addWidget(QLabel("目标语言"), 2, 0)
        layout.addWidget(self.target_language_combo, 2, 1)
        layout.addWidget(self.enhance_markdown_checkbox, 2, 2)
        layout.setColumnStretch(1, 1)
        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("导出与预览")
        layout = QGridLayout(group)

        self.output_path_edit = QLineEdit()
        self.export_pdf_checkbox = QCheckBox("同时导出 PDF")
        self.export_pdf_checkbox.toggled.connect(self.on_export_pdf_toggled)
        self.pdf_export_path_edit = QLineEdit()
        self.pdf_export_path_edit.setEnabled(False)

        output_btn = QPushButton("保存 Markdown")
        output_btn.clicked.connect(self.choose_output)
        self._mark_secondary(output_btn)

        pdf_output_btn = QPushButton("PDF 位置")
        pdf_output_btn.clicked.connect(self.choose_pdf_export_output)
        self._mark_secondary(pdf_output_btn)
        pdf_output_btn.setEnabled(False)
        self.pdf_export_btn = pdf_output_btn

        preview_btn = QPushButton("选择 Markdown 预览")
        preview_btn.clicked.connect(self.choose_markdown_preview)
        self._mark_secondary(preview_btn)

        layout.addWidget(QLabel("Markdown"), 0, 0)
        layout.addWidget(self.output_path_edit, 0, 1)
        layout.addWidget(output_btn, 0, 2)
        layout.addWidget(self.export_pdf_checkbox, 1, 0)
        layout.addWidget(self.pdf_export_path_edit, 1, 1)
        layout.addWidget(pdf_output_btn, 1, 2)
        layout.addWidget(preview_btn, 2, 0, 1, 3, alignment=Qt.AlignLeft)
        layout.setColumnStretch(1, 1)
        return group

    def _build_profile_group(self) -> QGroupBox:
        group = QGroupBox("模型与接口")
        layout = QGridLayout(group)

        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.load_selected_profile)
        self.profile_name_edit = QLineEdit()
        self.api_base_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.textChanged.connect(self.update_primary_api_key_summary)
        self.primary_key_summary_label = QLabel("未设置")
        self.primary_key_summary_label.setProperty("variant", "muted")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入额外 API Key")
        self.api_keys_list = QListWidget()
        self.model_edit = QLineEdit()
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 16)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.0, 30.0)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSingleStep(0.1)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)

        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_profile)
        delete_btn = QPushButton("删除配置")
        self._mark_secondary(delete_btn)
        delete_btn.clicked.connect(self.delete_profile)
        add_key_btn = QPushButton("加入")
        add_key_btn.clicked.connect(self.add_api_key_entry)
        self._mark_secondary(add_key_btn)
        remove_key_btn = QPushButton("移除选中")
        remove_key_btn.clicked.connect(self.remove_selected_api_key)
        self._mark_secondary(remove_key_btn)
        clear_keys_btn = QPushButton("清空")
        clear_keys_btn.clicked.connect(self.clear_api_keys)
        self._mark_secondary(clear_keys_btn)
        toggle_primary_key_btn = QPushButton("显示")
        toggle_primary_key_btn.clicked.connect(self.toggle_primary_api_key_visibility)
        self._mark_secondary(toggle_primary_key_btn)
        self.toggle_primary_key_btn = toggle_primary_key_btn

        key_actions = QHBoxLayout()
        key_actions.addWidget(add_key_btn)
        key_actions.addWidget(remove_key_btn)
        key_actions.addWidget(clear_keys_btn)
        key_actions.addStretch(1)

        primary_key_row = QHBoxLayout()
        primary_key_row.addWidget(self.api_key_edit, 1)
        primary_key_row.addWidget(toggle_primary_key_btn)

        layout.addWidget(QLabel("配置"), 0, 0)
        layout.addWidget(self.profile_combo, 0, 1)
        layout.addWidget(QLabel("配置名"), 0, 2)
        layout.addWidget(self.profile_name_edit, 0, 3)
        layout.addWidget(QLabel("API Base"), 1, 0)
        layout.addWidget(self.api_base_edit, 1, 1, 1, 3)
        layout.addWidget(QLabel("API Key"), 2, 0)
        layout.addLayout(primary_key_row, 2, 1, 1, 3)
        layout.addWidget(self.primary_key_summary_label, 3, 1, 1, 3)
        layout.addWidget(QLabel("额外 Key"), 4, 0)
        layout.addWidget(self.api_key_input, 4, 1, 1, 3)
        layout.addLayout(key_actions, 5, 1, 1, 3)
        layout.addWidget(self.api_keys_list, 6, 1, 2, 3)
        layout.addWidget(QLabel("模型"), 8, 0)
        layout.addWidget(self.model_edit, 8, 1)
        layout.addWidget(QLabel("Temperature"), 8, 2)
        layout.addWidget(self.temperature_spin, 8, 3)
        layout.addWidget(QLabel("并发数"), 9, 0)
        layout.addWidget(self.concurrent_spin, 9, 1)
        layout.addWidget(QLabel("请求间隔(s)"), 9, 2)
        layout.addWidget(self.interval_spin, 9, 3)
        layout.addWidget(QLabel("超时(s)"), 10, 0)
        layout.addWidget(self.timeout_spin, 10, 1)
        layout.addWidget(save_btn, 10, 2)
        layout.addWidget(delete_btn, 10, 3)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        return group

    def _build_appearance_group(self) -> QGroupBox:
        group = QGroupBox("界面")
        layout = QHBoxLayout(group)
        self.dark_mode_checkbox = QCheckBox("暗色模式")
        self.dark_mode_checkbox.toggled.connect(self.on_dark_mode_toggled)
        layout.addWidget(self.dark_mode_checkbox)
        layout.addStretch(1)
        return group

    def _build_section_group(self) -> QGroupBox:
        group = QGroupBox("章节选择")
        layout = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        read_btn = QPushButton("读取目录")
        read_btn.clicked.connect(self.load_pdf_structure)
        select_all_btn = QPushButton("全选")
        deselect_all_btn = QPushButton("全不选")
        self._mark_secondary(select_all_btn)
        self._mark_secondary(deselect_all_btn)
        select_all_btn.clicked.connect(self.select_all_sections)
        deselect_all_btn.clicked.connect(self.deselect_all_sections)
        btn_row.addWidget(read_btn)
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(deselect_all_btn)
        btn_row.addStretch(1)

        self.sections_list = QListWidget()
        self.sections_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.sections_list.setMinimumHeight(260)
        self.sections_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addLayout(btn_row)
        layout.addWidget(self.sections_list)
        return group

    def _build_queue_group(self) -> QGroupBox:
        group = QGroupBox("任务队列")
        layout = QVBoxLayout(group)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("加入队列")
        remove_btn = QPushButton("移除选中")
        clear_btn = QPushButton("清空队列")
        self._mark_secondary(remove_btn)
        self._mark_secondary(clear_btn)
        add_btn.clicked.connect(self.add_current_job_to_queue)
        remove_btn.clicked.connect(self.remove_selected_queue_job)
        clear_btn.clicked.connect(self.clear_queue)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        self.queue_list = QListWidget()
        layout.addLayout(btn_row)
        layout.addWidget(self.queue_list)
        return group

    def _build_control_group(self) -> QGroupBox:
        group = QGroupBox("执行")
        layout = QHBoxLayout(group)
        start_btn = QPushButton("开始当前任务")
        resume_btn = QPushButton("继续断点")
        queue_btn = QPushButton("开始队列")
        stop_btn = QPushButton("停止")
        clear_checkpoint_btn = QPushButton("清除断点")
        self._mark_secondary(resume_btn)
        self._mark_secondary(clear_checkpoint_btn)
        self._mark_secondary(stop_btn)
        start_btn.clicked.connect(self.start_current_translation)
        resume_btn.clicked.connect(self.resume_translation)
        queue_btn.clicked.connect(self.start_queue_translation)
        stop_btn.clicked.connect(self.stop_translation)
        clear_checkpoint_btn.clicked.connect(self.clear_checkpoint)
        layout.addWidget(start_btn)
        layout.addWidget(resume_btn)
        layout.addWidget(queue_btn)
        layout.addWidget(stop_btn)
        layout.addWidget(clear_checkpoint_btn)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("运行日志")
        group.setCheckable(True)
        group.setChecked(True)
        group.toggled.connect(self.on_log_toggled)
        self.log_group = group
        layout = QVBoxLayout(group)
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(100)
        layout.addWidget(self.log_edit)
        group.setMaximumHeight(180)
        return group

    def _mark_secondary(self, button: QPushButton) -> None:
        button.setProperty("variant", "secondary")
        button.style().unpolish(button)
        button.style().polish(button)

    def _load_config_to_ui(self) -> None:
        if not self.config.profiles:
            self.config.profiles.append(
                ProviderProfile(
                    name="Default",
                    api_base="https://api.openai.com/v1",
                    api_key="",
                    model="gpt-4.1-mini",
                    temperature=0.0,
                    max_concurrency=2,
                    min_request_interval=0.8,
                    timeout=180,
                )
            )
            self.config.selected_profile = "Default"
            self.config_store.save(self.config)

        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems([profile.name for profile in self.config.profiles])
        self.profile_combo.blockSignals(False)

        selected_index = 0
        for index, profile in enumerate(self.config.profiles):
            if profile.name == self.config.selected_profile:
                selected_index = index
                break
        self.profile_combo.setCurrentIndex(selected_index)
        self.load_selected_profile()

        self.pdf_path_edit.setText(self.config.last_pdf_path)
        self.output_path_edit.setText(self.config.last_output_path)
        self.pdf_export_path_edit.setText(self.config.last_pdf_export_path)
        self.target_language_combo.setCurrentText(self.config.last_target_language)
        self.enhance_markdown_checkbox.setChecked(self.config.enhance_markdown)
        self.export_pdf_checkbox.setChecked(self.config.export_pdf)
        self.dark_mode_checkbox.setChecked(self.config.dark_mode)
        if self.output_path_edit.text().strip():
            self.sync_preview_to_output()
        if self.output_path_edit.text().strip() and not self.pdf_export_path_edit.text().strip():
            self.sync_pdf_export_path()

    def _current_mode(self) -> str:
        return "all" if self.mode_all_radio.isChecked() else "selected"

    def _current_profile(self) -> ProviderProfile:
        return ProviderProfile(
            name=self.profile_name_edit.text().strip() or "Unnamed",
            api_base=self.api_base_edit.text().strip(),
            api_key=self.api_key_edit.text().strip(),
            model=self.model_edit.text().strip(),
            api_keys=list(self.extra_api_keys),
            temperature=self.temperature_spin.value(),
            max_concurrency=self.concurrent_spin.value(),
            min_request_interval=self.interval_spin.value(),
            timeout=self.timeout_spin.value(),
        )

    def _current_settings(self) -> TranslationSettings:
        settings = self._current_profile().to_settings()
        settings.target_language = self.target_language_combo.currentText().strip() or "中文"
        settings.enhance_markdown = self.enhance_markdown_checkbox.isChecked()
        return settings

    def choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        self.pdf_path_edit.setText(path)
        if not self.output_path_edit.text().strip():
            self.output_path_edit.setText(os.path.splitext(path)[0] + "_translated.md")
        self.sync_preview_to_output()
        self.sync_pdf_export_path()
        self.persist_session_paths()

    def choose_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存 Markdown", "", "Markdown Files (*.md)")
        if not path:
            return
        self.output_path_edit.setText(path)
        self.sync_preview_to_output()
        self.sync_pdf_export_path(force=True)
        self.persist_session_paths()

    def choose_pdf_export_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存 PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        self.pdf_export_path_edit.setText(path)
        self.persist_session_paths()

    def persist_session_paths(self) -> None:
        self.config.last_pdf_path = self.pdf_path_edit.text().strip()
        self.config.last_output_path = self.output_path_edit.text().strip()
        self.config.last_pdf_export_path = self.pdf_export_path_edit.text().strip()
        self.config.last_target_language = self.target_language_combo.currentText().strip() or "中文"
        self.config.export_pdf = self.export_pdf_checkbox.isChecked()
        self.config.enhance_markdown = self.enhance_markdown_checkbox.isChecked()
        self.config_store.save(self.config)

    def sync_pdf_export_path(self, force: bool = False) -> None:
        markdown_path = self.output_path_edit.text().strip()
        if not markdown_path:
            return
        current_pdf_path = self.pdf_export_path_edit.text().strip()
        default_pdf_path = os.path.splitext(markdown_path)[0] + ".pdf"
        if force or not current_pdf_path:
            self.pdf_export_path_edit.setText(default_pdf_path)

    def on_export_pdf_toggled(self, checked: bool) -> None:
        self.pdf_export_path_edit.setEnabled(checked)
        self.pdf_export_btn.setEnabled(checked)
        if checked:
            self.sync_pdf_export_path()
        self.persist_session_paths()

    def choose_markdown_preview(self) -> None:
        initial_path = self.output_path_edit.text().strip()
        initial_dir = os.path.dirname(initial_path) if initial_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "选择 Markdown 预览", initial_dir, "Markdown Files (*.md)")
        if not path:
            return
        self.preview_follows_output = False
        self.load_preview_markdown(path, switch_tab=True)

    def on_mode_changed(self) -> None:
        sender = self.sender()
        if isinstance(sender, QRadioButton) and not sender.isChecked():
            return
        self.sections_list.setEnabled(self._current_mode() == "selected")
        self.append_log("翻译范围已切换。")

    def on_log_toggled(self, checked: bool) -> None:
        self.log_edit.setVisible(checked)
        self.log_group.setMaximumHeight(180 if checked else 28)
        self.log_group.setMinimumHeight(110 if checked else 28)

    def load_selected_profile(self) -> None:
        if self.profile_combo.currentIndex() < 0:
            return
        profile = self.config.profiles[self.profile_combo.currentIndex()]
        self.profile_name_edit.setText(profile.name)
        self.api_base_edit.setText(profile.api_base)
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.toggle_primary_key_btn.setText("显示")
        self.api_key_edit.setText(profile.api_key)
        self.extra_api_keys = list(profile.api_keys)
        self.api_key_input.clear()
        self.refresh_api_keys_display()
        self.update_primary_api_key_summary()
        self.model_edit.setText(profile.model)
        self.temperature_spin.setValue(profile.temperature)
        self.concurrent_spin.setValue(profile.max_concurrency)
        self.interval_spin.setValue(profile.min_request_interval)
        self.timeout_spin.setValue(profile.timeout)
        self.config.selected_profile = profile.name
        self.config_store.save(self.config)

    def save_profile(self) -> None:
        profile = self._current_profile()
        for index, current in enumerate(self.config.profiles):
            if current.name == profile.name:
                self.config.profiles[index] = profile
                break
        else:
            self.config.profiles.append(profile)
        self.config.selected_profile = profile.name
        self.config_store.save(self.config)
        self._load_config_to_ui()
        self.append_log(f"已保存配置：{profile.name}")

    def delete_profile(self) -> None:
        name = self.profile_name_edit.text().strip()
        if not name:
            return
        self.config.profiles = [profile for profile in self.config.profiles if profile.name != name]
        if not self.config.profiles:
            self.config.profiles.append(
                ProviderProfile(
                    name="Default",
                    api_base="https://api.openai.com/v1",
                    api_key="",
                    model="gpt-4.1-mini",
                    target_language="中文",
                )
            )
        self.config.selected_profile = self.config.profiles[0].name
        self.config_store.save(self.config)
        self._load_config_to_ui()
        self.append_log(f"已删除配置：{name}")

    def load_pdf_structure(self) -> None:
        pdf_path = self.pdf_path_edit.text().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            QMessageBox.critical(self, "错误", "请先选择存在的 PDF 文件。")
            return
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(pdf_path)
            toc_items = load_toc(self.doc)
            self.sections = build_sections_from_toc(self.doc, toc_items)
            if not self.sections:
                self.sections = [build_full_document_section(self.doc)]

            self.sections_list.clear()
            for section in self.sections:
                label = f"{'  ' * max(0, section.level - 1)}{section.title} (第 {section.start_page}-{section.end_page} 页)"
                item = QListWidgetItem(label)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.sections_list.addItem(item)

            summary = (
                f"页数：{self.doc.page_count} | 章节数：{len(self.sections)}"
                if toc_items
                else f"页数：{self.doc.page_count} | 未检测到目录，按全文处理"
            )
            self.summary_label.setText(summary)
            self.set_status("PDF 目录读取完成")
            self.append_log(summary)
        except Exception as exc:
            QMessageBox.critical(self, "读取 PDF 失败", str(exc))

    def select_all_sections(self) -> None:
        for index in range(self.sections_list.count()):
            self.sections_list.item(index).setCheckState(Qt.Checked)

    def deselect_all_sections(self) -> None:
        for index in range(self.sections_list.count()):
            self.sections_list.item(index).setCheckState(Qt.Unchecked)

    def get_selected_sections(self) -> List[Section]:
        sections = []
        for index, section in enumerate(self.sections):
            item = self.sections_list.item(index)
            if item and item.checkState() == Qt.Checked:
                sections.append(section)
        return sections

    def validate_inputs(self, require_api: bool = True) -> bool:
        if not self.pdf_path_edit.text().strip() or not os.path.exists(self.pdf_path_edit.text().strip()):
            QMessageBox.critical(self, "错误", "请先选择存在的 PDF 文件。")
            return False
        if require_api:
            settings = self._current_settings()
            if not settings.api_base or not settings.model:
                QMessageBox.critical(self, "错误", "请完整填写 API Base、模型和目标语言。")
                return False
            if not settings.api_key and not settings.api_keys:
                QMessageBox.critical(self, "错误", "请至少填写一个 API Key。")
                return False
        if not self.output_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "请设置输出 Markdown 路径。")
            return False
        if self.export_pdf_checkbox.isChecked() and not self.pdf_export_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "已启用 PDF 导出，请设置 PDF 输出路径。")
            return False
        return True

    def ensure_sections_loaded(self) -> None:
        if not self.sections:
            self.load_pdf_structure()

    def build_job_from_ui(self) -> Optional[JobConfig]:
        if not self.validate_inputs():
            return None
        self.ensure_sections_loaded()
        if not self.sections:
            return None

        selected_sections = [build_full_document_section(self.doc)] if self._current_mode() == "all" else self.get_selected_sections()
        if self._current_mode() == "selected" and not selected_sections:
            QMessageBox.critical(self, "错误", "当前模式为仅翻译所选章节，请至少勾选一个章节。")
            return None

        self.persist_session_paths()
        return JobConfig(
            pdf_path=os.path.abspath(self.pdf_path_edit.text().strip()),
            output_path=os.path.abspath(self.output_path_edit.text().strip()),
            translate_mode=self._current_mode(),
            selected_sections=[asdict(section) for section in selected_sections],
            settings=asdict(self._current_settings()),
            export_pdf=self.export_pdf_checkbox.isChecked(),
            pdf_output_path=os.path.abspath(self.pdf_export_path_edit.text().strip())
            if self.export_pdf_checkbox.isChecked()
            else "",
        )

    def add_current_job_to_queue(self) -> None:
        job = self.build_job_from_ui()
        if not job:
            return
        self.job_queue.append(job)
        self.refresh_queue_display()
        self.append_log(f"已加入队列：{os.path.basename(job.pdf_path)}")

    def remove_selected_queue_job(self) -> None:
        row = self.queue_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中一个队列任务。")
            return
        removed = self.job_queue.pop(row)
        self.refresh_queue_display()
        self.append_log(f"已移除队列任务：{os.path.basename(removed.pdf_path)}")

    def clear_queue(self) -> None:
        self.job_queue.clear()
        self.refresh_queue_display()
        self.append_log("队列已清空。")

    def refresh_queue_display(self) -> None:
        self.queue_list.clear()
        for job in self.job_queue:
            mode_text = "全文" if job.translate_mode == "all" else f"选章({len(job.selected_sections)})"
            export_text = " +PDF" if job.export_pdf else ""
            self.queue_list.addItem(
                f"{os.path.basename(job.pdf_path)} -> {os.path.basename(job.output_path)}{export_text} [{mode_text}]"
            )
        self.queue_label.setText(f"队列：{len(self.job_queue)} 个任务")

    def _run_async(self, coroutine_factory) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "提示", "已有翻译任务正在运行。")
            return
        self.runner.stop_requested = False
        self.worker_thread = WorkerThread(coroutine_factory)
        self.worker_thread.log_signal.connect(self.append_log)
        self.worker_thread.status_signal.connect(self.set_status)
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.finished_signal.connect(self.on_worker_finished)
        self.worker_thread.start()

    def _build_thread_runner(self) -> TranslationRunner:
        if not self.worker_thread:
            raise RuntimeError("worker thread not initialized")
        self.runner = TranslationRunner(
            state_store=self.state_store,
            log_callback=self.worker_thread.log_signal.emit,
            status_callback=self.worker_thread.status_signal.emit,
            progress_callback=self.worker_thread.progress_signal.emit,
        )
        return self.runner

    def start_current_translation(self) -> None:
        job = self.build_job_from_ui()
        if not job:
            return
        if os.path.exists(job.output_path):
            answer = QMessageBox.question(self, "确认覆盖", "输出 Markdown 已存在，开始新翻译将覆盖该文件，是否继续？")
            if answer != QMessageBox.Yes:
                return

        async def task():
            runner = self._build_thread_runner()
            state = runner.create_state(job)
            self.state_store.save(state)
            if os.path.exists(job.output_path):
                os.remove(job.output_path)
            await runner.run_state(state)

        self._run_async(task)

    def resume_translation(self) -> None:
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.critical(self, "错误", "请先设置输出 Markdown 路径。")
            return
        checkpoint = state_file_path(output_path)
        if not os.path.exists(checkpoint):
            QMessageBox.critical(self, "错误", "未找到断点文件。")
            return

        async def task():
            runner = self._build_thread_runner()
            state = self.state_store.load(output_path)
            await runner.run_state(state)

        self._run_async(task)

    def start_queue_translation(self) -> None:
        if not self.job_queue:
            QMessageBox.warning(self, "提示", "队列为空。")
            return

        queue_snapshot = list(self.job_queue)

        async def task():
            runner = self._build_thread_runner()
            total = len(queue_snapshot)
            for index, job in enumerate(queue_snapshot, start=1):
                if runner.stop_requested:
                    break
                self.worker_thread.status_signal.emit(f"队列任务 {index}/{total}")
                checkpoint = state_file_path(job.output_path)
                if os.path.exists(checkpoint):
                    state = self.state_store.load(job.output_path)
                else:
                    state = runner.create_state(job)
                    self.state_store.save(state)
                    if os.path.exists(job.output_path):
                        os.remove(job.output_path)
                await runner.run_state(state)

        self._run_async(task)

    def clear_checkpoint(self) -> None:
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.critical(self, "错误", "请先设置输出 Markdown 路径。")
            return
        checkpoint = state_file_path(output_path)
        if os.path.exists(checkpoint):
            os.remove(checkpoint)
            self.append_log("断点文件已删除。")
        else:
            self.append_log("未找到断点文件。")

    def stop_translation(self) -> None:
        self.runner.request_stop()
        self.set_status("正在停止...")
        self.append_log("已发送停止请求。")

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def append_log(self, message: str) -> None:
        self.log_edit.appendPlainText(message)

    def update_progress(self, current: int, total: int, percent: float, eta: float) -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current} / {total} ({percent:.1f}%) | 预计剩余：{format_seconds(eta)}")
        self.refresh_preview_if_possible()

    def on_worker_finished(self, success: bool, error_text: str) -> None:
        if not success:
            self.append_log(error_text)
            self.set_status("翻译中断，已保留断点")
            QMessageBox.critical(self, "任务失败", error_text)
        else:
            self.set_status("任务结束")
        self.refresh_preview_if_possible()

    def load_preview_markdown(self, markdown_path: str, switch_tab: bool = False) -> None:
        if not os.path.exists(markdown_path):
            QMessageBox.warning(self, "提示", "所选 Markdown 文件不存在。")
            return
        self.preview_markdown_path = markdown_path
        self.preview_path_label.setText(markdown_path)
        self.preview_browser.setHtml(load_markdown_html(markdown_path, dark_mode=self.config.dark_mode))
        if switch_tab:
            self.top_tabs.setCurrentIndex(1)

    def refresh_preview_if_possible(self) -> None:
        if self.preview_follows_output:
            self.sync_preview_to_output(refresh=False)
        if not self.preview_markdown_path:
            return
        if os.path.exists(self.preview_markdown_path):
            self.load_preview_markdown(self.preview_markdown_path)

    def on_dark_mode_toggled(self, checked: bool) -> None:
        self.config.dark_mode = checked
        self.apply_theme()
        self.persist_session_paths()
        self.refresh_preview_if_possible()

    def apply_theme(self) -> None:
        self.setStyleSheet(get_app_qss(self.config.dark_mode))

    def sync_preview_to_output(self, refresh: bool = True) -> None:
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            return
        self.preview_follows_output = True
        self.preview_markdown_path = output_path
        self.preview_path_label.setText(output_path)
        if refresh and os.path.exists(output_path):
            self.load_preview_markdown(output_path)

    def _masked_api_key(self, api_key: str) -> str:
        suffix = api_key[-4:] if len(api_key) >= 4 else api_key
        masked_prefix = "*" * max(len(api_key) - len(suffix), 4)
        return f"{masked_prefix}{suffix}"

    def refresh_api_keys_display(self) -> None:
        self.api_keys_list.clear()
        for index, api_key in enumerate(self.extra_api_keys, start=1):
            self.api_keys_list.addItem(f"Key {index}: {self._masked_api_key(api_key)}")

    def update_primary_api_key_summary(self) -> None:
        api_key = self.api_key_edit.text().strip()
        self.primary_key_summary_label.setText(self._masked_api_key(api_key) if api_key else "未设置")

    def toggle_primary_api_key_visibility(self) -> None:
        if self.api_key_edit.echoMode() == QLineEdit.Password:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.toggle_primary_key_btn.setText("隐藏")
            return
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.toggle_primary_key_btn.setText("显示")

    def add_api_key_entry(self) -> None:
        api_key = self.api_key_input.text().strip()
        if not api_key:
            return
        self.extra_api_keys.append(api_key)
        self.api_key_input.clear()
        self.refresh_api_keys_display()

    def remove_selected_api_key(self) -> None:
        row = self.api_keys_list.currentRow()
        if row < 0:
            return
        self.extra_api_keys.pop(row)
        self.refresh_api_keys_display()

    def clear_api_keys(self) -> None:
        self.extra_api_keys.clear()
        self.refresh_api_keys_display()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.doc:
            self.doc.close()
        self.persist_session_paths()
        super().closeEvent(event)


def launch() -> None:
    app = QApplication.instance() or QApplication([])
    window = PDFTranslatorMainWindow()
    window.show()
    app.exec()
