import unittest

from PyQt5.QtWidgets import QApplication, QLabel

from ui.session_workspace import SessionWorkspace


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance()
    if _APP is None:
        _APP = QApplication([])
    return _APP


class SessionWorkspaceTest(unittest.TestCase):
    def test_add_and_find_tabs(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")

        self.assertEqual(workspace.addTab(first, "First"), 0)
        self.assertEqual(workspace.addTab(second, "Second"), 1)

        self.assertEqual(workspace.count(), 2)
        self.assertIs(workspace.widget(0), first)
        self.assertIs(workspace.widget(1), second)
        self.assertEqual(workspace.indexOf(second), 1)
        self.assertEqual(workspace.tabText(0), "First")

    def test_split_current_right_moves_current_tab_to_new_pane(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")
        workspace.addTab(first, "First")
        workspace.addTab(second, "Second")

        workspace.split_current_right()

        self.assertEqual(workspace.count(), 2)
        self.assertEqual(len(workspace._panes), 2)
        self.assertIs(workspace.currentWidget(), second)
        self.assertEqual(workspace.indexOf(first), 0)
        self.assertEqual(workspace.indexOf(second), 1)

    def test_split_current_down_sets_vertical_orientation_for_first_split(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")
        workspace.addTab(first, "First")
        workspace.addTab(second, "Second")

        workspace.split_current_down()

        self.assertEqual(len(workspace._panes), 2)

    def test_single_tab_split_is_ignored(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        workspace.addTab(first, "First")

        workspace.split_current_right()

        self.assertEqual(workspace.count(), 1)
        self.assertEqual(len(workspace._panes), 1)
        self.assertIs(workspace.currentWidget(), first)

    def test_move_tab_between_panes_inserts_at_target_index(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")
        third = QLabel("third")
        workspace.addTab(first, "First")
        workspace.addTab(second, "Second")
        workspace.addTab(third, "Third")
        workspace.split_current_right()

        left_pane, right_pane = workspace._panes
        workspace._move_tab_between_panes(left_pane, 0, right_pane, 0)

        self.assertEqual(workspace.count(), 3)
        self.assertEqual(len(workspace._panes), 2)
        self.assertIs(right_pane.widget(0), first)
        self.assertIs(right_pane.widget(1), third)
        self.assertIs(workspace.currentWidget(), first)

    def test_moving_last_tab_between_panes_removes_empty_pane(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")
        workspace.addTab(first, "First")
        workspace.addTab(second, "Second")
        workspace.split_current_right()

        left_pane, right_pane = workspace._panes
        workspace._move_tab_between_panes(left_pane, 0, right_pane, 0)

        self.assertEqual(workspace.count(), 2)
        self.assertEqual(len(workspace._panes), 1)
        self.assertIs(workspace.widget(0), first)
        self.assertIs(workspace.widget(1), second)

    def test_merge_all_tabs_restores_single_pane(self):
        ensure_app()
        workspace = SessionWorkspace()
        first = QLabel("first")
        second = QLabel("second")
        workspace.addTab(first, "First")
        workspace.addTab(second, "Second")
        workspace.split_current_right()

        workspace.merge_all_tabs()

        self.assertEqual(workspace.count(), 2)
        self.assertEqual(len(workspace._panes), 1)
        self.assertIs(workspace.widget(0), first)
        self.assertIs(workspace.widget(1), second)


if __name__ == "__main__":
    unittest.main()
