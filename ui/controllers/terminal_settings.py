import os
import platform
import subprocess

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)
from PyQt5.QtGui import QFontDatabase


class TerminalSettingsController:
    def __init__(self, main_window):
        self._main_window = main_window

    @property
    def _config(self):
        return self._main_window.app_config

    @property
    def _log_manager(self):
        return self._main_window._log_manager

    def show(self):
        dialog = QDialog(self._main_window)
        dialog.setWindowTitle("Terminal Settings")
        dialog.setMinimumWidth(450)

        layout = QVBoxLayout(dialog)

        terminal_controls = self._add_terminal_group(layout)
        controls = self._add_log_group(dialog, layout)
        cleanup_controls = self._add_cleanup_group(layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        self._apply_settings(
            scrollback_spin=terminal_controls["scrollback_spin"],
            font_family_combo=terminal_controls["font_family_combo"],
            font_size_spin=terminal_controls["font_size_spin"],
            log_enabled_cb=controls["log_enabled_cb"],
            log_timestamp_cb=controls["log_timestamp_cb"],
            log_dir_edit=controls["log_dir_edit"],
            log_name_edit=controls["log_name_edit"],
            auto_clean_cb=cleanup_controls["auto_clean_cb"],
            max_days_spin=cleanup_controls["max_days_spin"],
            max_total_spin=cleanup_controls["max_total_spin"],
            max_file_spin=cleanup_controls["max_file_spin"],
        )

    def _add_terminal_group(self, layout):
        group = QGroupBox("Terminal")
        form = QFormLayout(group)

        scrollback_spin = QSpinBox()
        scrollback_spin.setRange(100, 100000)
        scrollback_spin.setSingleStep(1000)
        scrollback_spin.setValue(self._config.scrollback_lines)
        scrollback_spin.setSuffix(" lines")
        form.addRow("Scrollback:", scrollback_spin)

        font_family_combo = QComboBox()
        font_family_combo.setEditable(True)
        font_family_combo.addItem("System Monospace", "")
        for family in QFontDatabase().families():
            font_family_combo.addItem(family, family)
        current_family = getattr(self._config, "terminal_font_family", "")
        index = font_family_combo.findData(current_family)
        if index >= 0:
            font_family_combo.setCurrentIndex(index)
        elif current_family:
            font_family_combo.setEditText(current_family)
        form.addRow("Font:", font_family_combo)

        font_size_spin = QSpinBox()
        font_size_spin.setRange(6, 48)
        font_size_spin.setValue(getattr(self._config, "terminal_font_size", 11))
        font_size_spin.setSuffix(" pt")
        form.addRow("Font size:", font_size_spin)

        info_label = QLabel("Number of terminal history lines kept in memory.")
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", info_label)

        layout.addWidget(group)
        return {
            "scrollback_spin": scrollback_spin,
            "font_family_combo": font_family_combo,
            "font_size_spin": font_size_spin,
        }

    def _add_log_group(self, dialog, layout):
        group = QGroupBox("Logging")
        form = QFormLayout(group)

        log_enabled_cb = QCheckBox("Enable logging")
        log_enabled_cb.setChecked(self._config.log_enabled)
        form.addRow("", log_enabled_cb)

        log_timestamp_cb = QCheckBox("Add timestamp to each line")
        log_timestamp_cb.setChecked(self._config.log_timestamp)
        form.addRow("", log_timestamp_cb)

        log_dir_edit = QLineEdit(self._config.log_dir)
        log_dir_edit.setReadOnly(True)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(lambda: self._browse_log_dir(dialog, log_dir_edit))

        log_dir_layout = QHBoxLayout()
        log_dir_layout.addWidget(log_dir_edit)
        log_dir_layout.addWidget(browse_btn)
        form.addRow("Log directory:", log_dir_layout)

        open_log_btn = QPushButton("Open Log Directory")
        open_log_btn.clicked.connect(lambda: self._open_log_dir(dialog, log_dir_edit.text()))
        form.addRow("", open_log_btn)

        log_name_edit = QLineEdit(self._config.log_name_pattern)
        form.addRow("Name pattern:", log_name_edit)

        hint = QLabel("Variables: {port}, {date}, {time}, {name}")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("", hint)

        layout.addWidget(group)
        return {
            "log_enabled_cb": log_enabled_cb,
            "log_timestamp_cb": log_timestamp_cb,
            "log_dir_edit": log_dir_edit,
            "log_name_edit": log_name_edit,
        }

    def _add_cleanup_group(self, layout):
        group = QGroupBox("Log Cleanup")
        form = QFormLayout(group)

        auto_clean_cb = QCheckBox("Enable automatic cleanup")
        auto_clean_cb.setChecked(self._config.log_auto_clean)
        form.addRow("", auto_clean_cb)

        max_days_spin = QSpinBox()
        max_days_spin.setRange(0, 3650)
        max_days_spin.setValue(self._config.log_max_days)
        max_days_spin.setSuffix(" days")
        max_days_spin.setSpecialValueText("Unlimited")
        form.addRow("Retention:", max_days_spin)

        max_total_spin = QSpinBox()
        max_total_spin.setRange(0, 100000)
        max_total_spin.setSingleStep(100)
        max_total_spin.setValue(self._config.log_max_total_size_mb)
        max_total_spin.setSuffix(" MB")
        max_total_spin.setSpecialValueText("Unlimited")
        form.addRow("Total limit:", max_total_spin)

        max_file_spin = QSpinBox()
        max_file_spin.setRange(0, 10000)
        max_file_spin.setSingleStep(10)
        max_file_spin.setValue(self._config.log_max_file_size_mb)
        max_file_spin.setSuffix(" MB")
        max_file_spin.setSpecialValueText("Unlimited")
        form.addRow("File limit:", max_file_spin)

        stats_label = QLabel(self._format_stats())
        stats_label.setStyleSheet("color: gray; font-size: 11px;")

        clean_now_btn = QPushButton("Clean Now")
        clean_now_btn.clicked.connect(lambda: self._clean_now(stats_label))

        stats_row = QHBoxLayout()
        stats_row.addWidget(stats_label)
        stats_row.addWidget(clean_now_btn)
        form.addRow("", stats_row)

        layout.addWidget(group)
        return {
            "auto_clean_cb": auto_clean_cb,
            "max_days_spin": max_days_spin,
            "max_total_spin": max_total_spin,
            "max_file_spin": max_file_spin,
        }

    def _browse_log_dir(self, dialog, log_dir_edit):
        directory = QFileDialog.getExistingDirectory(
            dialog,
            "Select Log Directory",
            self._config.log_dir,
        )
        if directory:
            log_dir_edit.setText(directory)

    def _open_log_dir(self, dialog, log_dir):
        if not os.path.exists(log_dir):
            QMessageBox.warning(dialog, "Warning", f"Log directory does not exist: {log_dir}")
            return

        if platform.system() == "Windows":
            os.startfile(log_dir)
        elif platform.system() == "Darwin":
            subprocess.run(["open", log_dir], check=False)
        else:
            subprocess.run(["xdg-open", log_dir], check=False)

    def _format_stats(self):
        stats = self._log_manager.get_stats()
        return f"Current usage: {stats['total_size_mb']} MB, {stats['file_count']} files"

    def _clean_now(self, stats_label):
        self._log_manager.force_cleanup()
        stats_label.setText(self._format_stats())

    def _apply_settings(
        self,
        scrollback_spin,
        font_family_combo,
        font_size_spin,
        log_enabled_cb,
        log_timestamp_cb,
        log_dir_edit,
        log_name_edit,
        auto_clean_cb,
        max_days_spin,
        max_total_spin,
        max_file_spin,
    ):
        config = self._config
        new_scrollback = scrollback_spin.value()
        font_family = font_family_combo.currentData()
        if font_family is None:
            font_family = font_family_combo.currentText().strip()
        font_size = font_size_spin.value()

        config.scrollback_lines = new_scrollback
        config.terminal_font_family = font_family
        config.terminal_font_size = font_size
        config.log_enabled = log_enabled_cb.isChecked()
        config.log_timestamp = log_timestamp_cb.isChecked()
        config.log_dir = log_dir_edit.text()
        config.log_name_pattern = log_name_edit.text() or "{port}_{date}_{time}"
        config.log_auto_clean = auto_clean_cb.isChecked()
        config.log_max_days = max_days_spin.value()
        config.log_max_total_size_mb = max_total_spin.value()
        config.log_max_file_size_mb = max_file_spin.value()

        self._main_window.config_manager.save()

        self._log_manager.log_dir = config.log_dir
        self._log_manager.name_pattern = config.log_name_pattern
        self._log_manager.max_days = config.log_max_days
        self._log_manager.max_total_size_mb = config.log_max_total_size_mb
        self._log_manager.max_file_size_mb = config.log_max_file_size_mb
        self._log_manager.auto_clean = config.log_auto_clean

        for _, tab, _ in self._main_window._sessions.values():
            if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_scrollback_lines"):
                tab.terminal.set_scrollback_lines(new_scrollback)
            if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_terminal_font"):
                tab.terminal.set_terminal_font(font_family, font_size)

        status = f"Settings updated: scrollback {new_scrollback} lines, font {font_size} pt"
        status += ", logging enabled" if config.log_enabled else ", logging disabled"
        self._main_window.statusbar.showMessage(status)
