"""
Reusable GUI widgets for the Transport Advisor
"""

from PyQt6.QtWidgets import QComboBox, QCompleter
from PyQt6.QtCore import Qt, pyqtSignal


class AutocompleteComboBox(QComboBox):
    """A combobox with autocomplete search functionality."""

    # Signal emitted when text changes after user selection
    textChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # Connect the edit text signal
        self.editTextChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text):
        self.textChanged.emit(text)

    def set_items(self, items):
        """Set the autocomplete items list."""
        self.clear()
        sorted_items = sorted(items)
        self.addItems(sorted_items)
        # Setup completer for autocomplete
        completer = QCompleter(sorted_items, self)
        completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.setCompleter(completer)

    def get_current_text(self):
        """Get the currently selected or typed text."""
        return self.currentText().strip()