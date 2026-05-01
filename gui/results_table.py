"""
Journey results table widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class ResultsTable(QWidget):
    """Widget for displaying journey results — click a row to highlight it on the map."""

    journeySelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.journeys = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Title
        title = QLabel("Journey Results")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["#", "Duration", "Cost (HKD)", "Segments", "Modes Used"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellClicked.connect(self._on_row_clicked)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.table)

        # Detail panel
        self.detail_panel = QLabel("← Select a journey above to see its step-by-step route")
        self.detail_panel.setWordWrap(True)
        self.detail_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.detail_panel.setStyleSheet(
            "padding: 10px; background-color: #181825; border-radius: 6px; "
            "font-size: 12px; color: #cdd6f4;"
        )
        self.detail_panel.setMinimumHeight(100)
        layout.addWidget(self.detail_panel)

    def set_journeys(self, journeys):
        """Populate the table with a list of Journey objects."""
        self.journeys = journeys
        self.table.setRowCount(len(journeys))

        for i, j in enumerate(journeys):
            modes = sorted({s.mode_of_transport for s in j.segments})
            mode_str = " + ".join(modes)

            items = [
                QTableWidgetItem(str(i + 1)),
                QTableWidgetItem(f"{j.total_duration} min"),
                QTableWidgetItem(f"${j.total_cost:.2f}"),
                QTableWidgetItem(str(j.num_segments)),
                QTableWidgetItem(mode_str),
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, col, item)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(4, max(180, self.table.columnWidth(4)))

    def clear(self):
        self.journeys = []
        self.table.setRowCount(0)
        self.detail_panel.setText("← Select a journey above to see its step-by-step route")

    def _on_row_clicked(self, row, _col):
        if 0 <= row < len(self.journeys):
            self.journeySelected.emit(row)
            self._show_detail(row)

    def _show_detail(self, index):
        if index < 0 or index >= len(self.journeys):
            return

        j = self.journeys[index]
        lines = [
            f"<b>Journey #{index + 1}</b> &nbsp;·&nbsp; "
            f"{j.total_duration} min &nbsp;·&nbsp; "
            f"${j.total_cost:.2f} HKD &nbsp;·&nbsp; "
            f"{j.num_segments} segment(s)<br>"
        ]

        # Group consecutive segments by mode for a cleaner display
        for k, seg in enumerate(j.segments, 1):
            mode_color = {
                "MTR":            "#89b4fa",
                "Bus":            "#a6e3a1",
                "Light Rail":     "#fab387",
                "Walk":           "#a6adc8",
                "Airport Express":"#cba6f7",
            }.get(seg.mode_of_transport, "#cdd6f4")

            lines.append(
                f"<span style='color:{mode_color};'><b>{k}.</b> "
                f"{seg.from_stop} → {seg.to_stop}</span> "
                f"<span style='color:#a6adc8;'>({seg.duration} min, "
                f"${seg.cost:.2f}, {seg.mode_of_transport})</span>"
            )

        self.detail_panel.setText("<br>".join(lines))
