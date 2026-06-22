from ui.dialogs import HighlightRulesDialog
from utils.config_schema import HighlightRuleData


HIGHLIGHT_COLORS = [
    "#ffec80",
    "#8cecff",
    "#a8f0a5",
    "#ffc078",
    "#c5a3ff",
    "#ff9ecb",
    "#91caff",
    "#ff8a8a",
]


class HighlightRulesController:
    def __init__(self, main_window):
        self._main_window = main_window

    def show(self, selected_text: str = ""):
        config = self._main_window.app_config
        dialog = HighlightRulesDialog(
            getattr(config, "highlight_rules", []),
            selected_text=selected_text,
            parent=self._main_window,
        )
        if dialog.exec_() != dialog.Accepted:
            return
        config.highlight_rules = dialog.get_rules()
        self._main_window.config_manager.save()
        self.apply_to_open_terminals()
        self._main_window.statusbar.showMessage(
            f"Updated {len(config.highlight_rules)} highlight rule(s)"
        )

    def clear(self):
        self._main_window.app_config.highlight_rules = []
        self._main_window.config_manager.save()
        self.apply_to_open_terminals()
        self._main_window.statusbar.showMessage("Cleared highlight rules")

    def add_selection(self, text: str):
        text = (text or "").strip()
        if not text:
            self._main_window.statusbar.showMessage("Select text before highlighting")
            return

        config = self._main_window.app_config
        rules = list(getattr(config, "highlight_rules", []))
        for rule in rules:
            if not getattr(rule, "regex", False) and rule.pattern == text:
                rule.enabled = True
                self._main_window.statusbar.showMessage(f"Highlight already exists: {text}")
                self.apply_to_open_terminals()
                return

        color = HIGHLIGHT_COLORS[len(rules) % len(HIGHLIGHT_COLORS)]
        rules.append(
            HighlightRuleData(
                name=text[:32],
                pattern=text,
                color=color,
                case_sensitive=False,
                regex=False,
                enabled=True,
            )
        )
        config.highlight_rules = rules
        self._main_window.config_manager.save()
        self.apply_to_open_terminals()
        self._main_window.statusbar.showMessage(f"Added highlight: {text}")

    def apply_to_open_terminals(self):
        rules = getattr(self._main_window.app_config, "highlight_rules", [])
        for _, tab, _ in self._main_window._sessions.values():
            if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_highlight_rules"):
                tab.terminal.set_highlight_rules(rules)
