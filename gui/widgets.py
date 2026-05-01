"""
Reusable GUI widgets for the Transport Advisor
"""

from PyQt6.QtWidgets import QComboBox, QCompleter
from PyQt6.QtCore import Qt, pyqtSignal


class AutocompleteComboBox(QComboBox):
    """A combobox with real-time filtered autocomplete search."""

    textChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(12)
        self.editTextChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text):
        self.textChanged.emit(text)

    def set_items(self, items):
        """Set the autocomplete items list with filtered popup completion."""
        self.clear()
        sorted_items = sorted(items)
        self.addItems(sorted_items)

        completer = QCompleter(sorted_items, self)
        # PopupCompletion + MatchContains = filters as you type, matches anywhere in name
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)

    def get_current_text(self) -> str:
        """Get the currently selected or typed text."""
        return self.currentText().strip()
