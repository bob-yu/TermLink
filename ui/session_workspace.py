"""Split-capable session workspace."""

from PyQt5.QtCore import QMimeData, QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QDrag, QFont, QPainter
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QSplitter,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


TAB_MIME_TYPE = "application/x-termlink-session-tab"


class SessionTabBar(QTabBar):
    """Tab bar that supports moving tabs between session panes."""

    tab_drop_requested = pyqtSignal(object, int, object, int)

    _drag_source = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._press_pos = None
        self._press_index = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.pos()
            self._press_index = self.tabAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._press_pos is None or self._press_index < 0:
            super().mouseMoveEvent(event)
            return
        if (event.pos() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        source_pane = self.parentWidget()
        SessionTabBar._drag_source = (source_pane, self._press_index)

        mime = QMimeData()
        mime.setData(TAB_MIME_TYPE, b"tab")
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)

        SessionTabBar._drag_source = None
        self._press_pos = None
        self._press_index = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(TAB_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        source = SessionTabBar._drag_source
        if not source or not event.mimeData().hasFormat(TAB_MIME_TYPE):
            super().dropEvent(event)
            return

        source_pane, source_index = source
        target_pane = self.parentWidget()
        target_index = self.tabAt(event.pos())
        if target_index < 0:
            target_index = target_pane.count()

        self.tab_drop_requested.emit(source_pane, source_index, target_pane, target_index)
        event.acceptProposedAction()


class SessionPane(QTabWidget):
    """One tab pane in the split workspace."""

    tab_context_requested = pyqtSignal(object, int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        tab_bar = SessionTabBar(self)
        self.setTabBar(tab_bar)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #d8dee4;
            }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #d8dee4;
                border-bottom: none;
                color: #24292f;
                padding: 6px 28px 6px 10px;
                min-height: 22px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-top: 2px solid #0969da;
            }
            QTabBar::tab:hover:!selected {
                background: #eef2f7;
            }
            QTabBar::close-button {
                image: url(ui/resources/icons/x.svg);
                subcontrol-position: right;
                width: 14px;
                height: 14px;
                margin-right: 7px;
            }
            QTabBar::close-button:hover {
                background: #e2e8f0;
                border-radius: 4px;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() != 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setPen(QColor("#c5ccd6"))
        font = QFont(self.font())
        font.setPointSize(50)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "TermLink")

    def _show_tab_context_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return
        menu = QMenu(self)
        self.tab_context_requested.emit(self, index, menu)
        if not menu.isEmpty():
            menu.exec_(self.tabBar().mapToGlobal(pos))


class SessionWorkspace(QWidget):
    """A QTabWidget-compatible workspace with split panes."""

    tabCloseRequested = pyqtSignal(int)
    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QSplitter(Qt.Horizontal, self)
        self._panes = []
        self._active_pane = None
        self._create_pane(self._root)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._root)

    def addTab(self, widget, title):
        pane = self._active_pane or self._panes[0]
        index = pane.addTab(widget, title)
        pane.setCurrentIndex(index)
        self._active_pane = pane
        return self.indexOf(widget)

    def removeTab(self, index):
        pane, local_index = self._pane_and_local_index(index)
        if pane is None:
            return
        pane.removeTab(local_index)
        self._remove_empty_panes()

    def setCurrentIndex(self, index):
        pane, local_index = self._pane_and_local_index(index)
        if pane is None:
            return
        self._active_pane = pane
        pane.setCurrentIndex(local_index)

    def currentIndex(self):
        return self.indexOf(self.currentWidget())

    def currentWidget(self):
        if self._active_pane is None:
            return None
        return self._active_pane.currentWidget()

    def count(self):
        return sum(pane.count() for pane in self._panes)

    def widget(self, index):
        pane, local_index = self._pane_and_local_index(index)
        return pane.widget(local_index) if pane is not None else None

    def indexOf(self, widget):
        offset = 0
        for pane in self._panes:
            local_index = pane.indexOf(widget)
            if local_index >= 0:
                return offset + local_index
            offset += pane.count()
        return -1

    def tabText(self, index):
        pane, local_index = self._pane_and_local_index(index)
        return pane.tabText(local_index) if pane is not None else ""

    def setTabText(self, index, title):
        pane, local_index = self._pane_and_local_index(index)
        if pane is not None:
            pane.setTabText(local_index, title)

    def setTabToolTip(self, index, tooltip):
        pane, local_index = self._pane_and_local_index(index)
        if pane is not None:
            pane.setTabToolTip(local_index, tooltip)

    def setTabsClosable(self, closable):
        for pane in self._panes:
            pane.setTabsClosable(closable)

    def split_current_right(self):
        self._split_current(Qt.Horizontal)

    def split_current_down(self):
        self._split_current(Qt.Vertical)

    def merge_all_tabs(self):
        if len(self._panes) <= 1:
            return
        target = self._active_pane or self._panes[0]
        tabs = []
        for pane in list(self._panes):
            while pane.count() > 0:
                widget = pane.widget(0)
                title = pane.tabText(0)
                tooltip = pane.tabToolTip(0)
                pane.removeTab(0)
                tabs.append((widget, title, tooltip))
        for widget, title, tooltip in tabs:
            index = target.addTab(widget, title)
            target.setTabToolTip(index, tooltip)
        target.setCurrentIndex(max(0, target.count() - 1))
        self._active_pane = target
        self._remove_empty_panes(keep_one=True)
        self._refresh_tabs([widget for widget, _title, _tooltip in tabs])
        self.currentChanged.emit(self.currentIndex())

    def _split_current(self, orientation):
        pane = self._active_pane
        if pane is None or pane.count() == 0:
            return
        if pane.count() < 2:
            return
        index = pane.currentIndex()
        widget = pane.widget(index)
        title = pane.tabText(index)
        tooltip = pane.tabToolTip(index)
        pane.removeTab(index)

        if self._root.orientation() != orientation and len(self._panes) <= 1:
            self._root.setOrientation(orientation)

        new_pane = self._create_pane(self._root)
        new_index = new_pane.addTab(widget, title)
        new_pane.setTabToolTip(new_index, tooltip)
        new_pane.setCurrentIndex(new_index)
        self._active_pane = new_pane
        self._refresh_tabs([widget])
        self.currentChanged.emit(self.indexOf(widget))

    def _create_pane(self, parent):
        pane = SessionPane(parent)
        pane.tabCloseRequested.connect(lambda local_index, p=pane: self._on_tab_close_requested(p, local_index))
        pane.currentChanged.connect(lambda _index, p=pane: self._on_pane_current_changed(p))
        pane.tab_context_requested.connect(self._populate_tab_context_menu)
        pane.tabBar().tab_drop_requested.connect(self._move_tab_between_panes)
        self._panes.append(pane)
        self._active_pane = pane
        parent.addWidget(pane)
        return pane

    def _move_tab_between_panes(self, source_pane, source_index, target_pane, target_index):
        if source_pane not in self._panes or target_pane not in self._panes:
            return
        if source_index < 0 or source_index >= source_pane.count():
            return
        if source_pane is target_pane:
            if target_index > source_index:
                target_index -= 1
            target_index = max(0, min(target_index, source_pane.count() - 1))
            if target_index != source_index:
                source_pane.tabBar().moveTab(source_index, target_index)
            source_pane.setCurrentIndex(target_index)
            self._active_pane = source_pane
            self.currentChanged.emit(self._global_index(source_pane, target_index))
            return

        widget = source_pane.widget(source_index)
        title = source_pane.tabText(source_index)
        tooltip = source_pane.tabToolTip(source_index)
        source_pane.removeTab(source_index)

        target_index = max(0, min(target_index, target_pane.count()))
        target_pane.insertTab(target_index, widget, title)
        target_pane.setTabToolTip(target_index, tooltip)
        target_pane.setCurrentIndex(target_index)
        self._active_pane = target_pane
        self._remove_empty_panes(keep_one=True)
        self._refresh_tabs([widget])
        self.currentChanged.emit(self.indexOf(widget))

    def _refresh_tabs(self, tabs):
        for tab in tabs:
            terminal = getattr(tab, "terminal", None)
            if terminal is not None and hasattr(terminal, "refresh_layout"):
                QTimer.singleShot(0, terminal.refresh_layout)
                QTimer.singleShot(60, terminal.refresh_layout)

    def _on_tab_close_requested(self, pane, local_index):
        self._active_pane = pane
        self.tabCloseRequested.emit(self._global_index(pane, local_index))

    def _on_pane_current_changed(self, pane):
        if pane.count() <= 0:
            return
        self._active_pane = pane
        self.currentChanged.emit(self._global_index(pane, pane.currentIndex()))

    def _populate_tab_context_menu(self, pane, local_index, menu):
        self._active_pane = pane
        pane.setCurrentIndex(local_index)
        if pane.count() >= 2:
            split_right = QAction("Split Right", menu)
            split_right.triggered.connect(self.split_current_right)
            split_down = QAction("Split Down", menu)
            split_down.triggered.connect(self.split_current_down)
            menu.addAction(split_right)
            menu.addAction(split_down)
        if len(self._panes) > 1:
            merge_tabs = QAction("Merge All Tabs", menu)
            merge_tabs.triggered.connect(self.merge_all_tabs)
            menu.addAction(merge_tabs)
        close_tab = QAction("Close", menu)
        close_tab.triggered.connect(lambda: self.tabCloseRequested.emit(self._global_index(pane, local_index)))
        if not menu.isEmpty():
            menu.addSeparator()
        menu.addAction(close_tab)

    def _pane_and_local_index(self, index):
        if index is None or index < 0:
            return None, -1
        offset = 0
        for pane in self._panes:
            if index < offset + pane.count():
                return pane, index - offset
            offset += pane.count()
        return None, -1

    def _global_index(self, pane, local_index):
        offset = 0
        for current in self._panes:
            if current is pane:
                return offset + local_index
            offset += current.count()
        return -1

    def _remove_empty_panes(self, keep_one=True):
        for pane in list(self._panes):
            if keep_one and len(self._panes) <= 1:
                break
            if pane.count() == 0:
                self._panes.remove(pane)
                pane.setParent(None)
                pane.deleteLater()
        if self._active_pane not in self._panes:
            self._active_pane = self._panes[0] if self._panes else self._create_pane(self._root)
