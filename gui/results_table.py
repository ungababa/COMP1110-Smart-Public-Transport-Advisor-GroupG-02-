"""
Journey results table widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal


class ResultsTable(QWidget):
    """Widget for displaying journey results in a table."""

    # Signal emitted when user clicks on a journey row
    journeySelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.journeys = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Journey Results")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "#", "Segments", "Duration", "Cost", "Transport Modes"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        # Details panel
        self.details_label = QLabel("Select a journey to see details")
        self.details_label.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.details_label.setStyleSheet("padding: 8px; background-color: #f0f0f0;")
        layout.addWidget(self.details_label)

    def set_journeys(self, journeys):
        """Set the journeys to display."""
        self.journeys = journeys
        self.table.setRowCount(len(journeys))

        for i, journey in enumerate(journeys):
            # Row number
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # Segments
            self.table.setItem(i, 1, QTableWidgetItem(str(journey.num_segments)))

            # Duration
            self.table.setItem(i, 2, QTableWidgetItem(f"{journey.total_duration} min"))

            # Cost
            self.table.setItem(i, 3, QTableWidgetItem(f"${journey.total_cost:.2f}"))

            # Transport modes
            modes = set(s.mode_of_transport for s in journey.segments)
            modes_str = ", ".join(sorted(modes))
            self.table.setItem(i, 4, QTableWidgetItem(modes_str))

        # Resize columns
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(4, max(150, self.table.columnWidth(4)))

    def clear(self):
        """Clear the results."""
        self.journeys = []
        self.table.setRowCount(0)
        self.details_label.setText("Select a journey to see details")

    def _on_cell_clicked(self, row, column):
        """Handle cell click."""
        if 0 <= row < len(self.journeys):
            self.journeySelected.emit(row)
            self._show_details(row)

    def _show_details(self, index):
        """Show journey details in the details panel."""
        if index < 0 or index >= len(self.journeys):
            return

        journey = self.journeys[index]
        lines = []
        lines.append(f"<b>Journey #{index + 1}</b>")
        lines.append(f"Total: {journey.total_duration} min, ${journey.total_cost:.2f}")
        lines.append("")
        lines.append("<b>Segments:</b>")

        for i, seg in enumerate(journey.segments, 1):
            lines.append(f"  {i}. {seg.from_stop} → {seg.to_stop}")
            lines.append(f"     {seg.duration} min, ${seg.cost:.2f} ({seg.mode_of_transport})")

        self.details_label.setText("<br>".join(lines))