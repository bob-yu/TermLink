from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.serial_access_server import SerialAccessMode


class RemoteLogDownloadController:
    """Remote server log download UI and transfer flow."""

    CHUNK_SIZE = 65536

    def __init__(self, main_window):
        self._main_window = main_window
        self._dialog = None

    @property
    def _network_client(self):
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        if remote_clients is not None:
            active = remote_clients.get(remote_clients.active_server_id)
            if active:
                return active
            first = remote_clients.first_connected()
            if first:
                _server_id, client = first
                return client
        return self._main_window._network_client

    @property
    def _app_config(self):
        return self._main_window.app_config

    def show(self):
        if (
            self._main_window._network_mode != SerialAccessMode.CLIENT
            or not self._network_client
        ):
            QMessageBox.warning(
                self._main_window,
                "Error",
                "Server log download is only available in client mode.",
            )
            return

        if not self._network_client.is_connected:
            QMessageBox.warning(
                self._main_window,
                "Error",
                "Not connected to the server.",
            )
            return

        self._network_client.request_log_list(self._app_config.log_dir)
        self._show_dialog()

    def _show_dialog(self):
        dialog = QDialog(self._main_window)
        dialog.setWindowTitle("Download Server Logs")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a log file to download:"))

        log_list = QListWidget()
        layout.addWidget(log_list)

        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        layout.addWidget(progress_bar)

        btn_layout = QHBoxLayout()

        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(
            lambda: self._start_log_download(log_list, progress_bar, dialog)
        )
        btn_layout.addWidget(download_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(
            lambda: self._network_client.request_log_list(self._app_config.log_dir)
        )
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        def on_log_list_received(files):
            log_list.clear()
            for file_info in files:
                item_text = (
                    f"{file_info['name']} "
                    f"({file_info['size']} bytes, {file_info['mtime']})"
                )
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, file_info["name"])
                log_list.addItem(item)

        self._network_client.log_list_received.connect(on_log_list_received)
        dialog.destroyed.connect(
            lambda: self._safe_disconnect(
                self._network_client.log_list_received, on_log_list_received
            )
        )

        self._dialog = dialog
        dialog.show()

    def _start_log_download(self, log_list, progress_bar, dialog):
        current_item = log_list.currentItem()
        if not current_item:
            QMessageBox.warning(dialog, "Warning", "Please select a log file.")
            return

        filename = current_item.data(Qt.UserRole)
        save_path, _ = QFileDialog.getSaveFileName(
            dialog,
            "Save Log File",
            filename,
            "Log Files (*.log);;All Files (*)",
        )
        if not save_path:
            return

        progress_bar.setVisible(True)
        progress_bar.setValue(0)
        self._download_log_file(filename, save_path, progress_bar, dialog)

    def _download_log_file(self, filename, save_path, progress_bar, dialog):
        download_state = {
            "offset": 0,
            "file": None,
        }

        def on_log_data_received(log_data):
            try:
                if log_data.get("filename") != filename:
                    return
                if log_data.get("offset") != download_state["offset"]:
                    return

                data = log_data.get("data", b"")
                if not download_state["file"]:
                    download_state["file"] = open(save_path, "wb")

                if data:
                    download_state["file"].write(data)
                    download_state["offset"] += len(data)
                    progress_bar.setValue(download_state["offset"] // 1024)
                    self._network_client.download_log(
                        self._app_config.log_dir,
                        filename,
                        download_state["offset"],
                        self.CHUNK_SIZE,
                    )
                    return

                self._finish_download(download_state, progress_bar)
                QMessageBox.information(
                    dialog,
                    "Success",
                    f"Log file saved to:\n{save_path}",
                )
                self._safe_disconnect(
                    self._network_client.log_data_received,
                    on_log_data_received,
                )

            except Exception as exc:
                self._finish_download(download_state, progress_bar)
                QMessageBox.critical(dialog, "Error", f"Download failed: {exc}")
                self._safe_disconnect(
                    self._network_client.log_data_received,
                    on_log_data_received,
                )

        self._network_client.log_data_received.connect(on_log_data_received)
        self._network_client.download_log(
            self._app_config.log_dir,
            filename,
            0,
            self.CHUNK_SIZE,
        )

    @staticmethod
    def _finish_download(download_state, progress_bar):
        if download_state.get("file"):
            download_state["file"].close()
            download_state["file"] = None
        progress_bar.setVisible(False)

    @staticmethod
    def _safe_disconnect(signal, callback):
        try:
            signal.disconnect(callback)
        except TypeError:
            pass
