"""
Journey results table widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


# Colour per transport mode — matches the map dots
MODE_COLORS = {
    "MTR":             ("#89b4fa", "#1e1e2e"),
    "Bus":             ("#a6e3a1", "#1e1e2e"),
    "Light Rail":      ("#fab387", "#1e1e2e"),
    "Walk":            ("#a6adc8", "#1e1e2e"),
    "Airport Express": ("#cba6f7", "#1e1e2e"),
}

MODE_ICONS = {
    "MTR":             "🚇",
    "Bus":             "🚌",
    "Light Rail":      "🚊",
    "Walk":            "🚶",
    "Airport Express": "✈️",
}


class ResultsTable(QWidget):
    """Ranked journey list + step-by-step detail panel."""

    journeySelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.journeys = []
        self._setup_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # ── Header ────────────────────────────────────────────────────────────
        header = QLabel("Journey Results")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 2px 0;")
        layout.addWidget(header)

        # ── Horizontal split: table left, detail panel right ──────────────────
        row = QHBoxLayout()
        row.setSpacing(8)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Time", "Cost", "Mode(s)"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumWidth(340)
        self.table.setMaximumWidth(420)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.table.cellClicked.connect(self._on_cell_clicked)
        row.addWidget(self.table)

        # Detail panel — scrollable
        self.detail_label = QLabel(
            "<span style='color:#6c7086;'>← Select a journey to see its step-by-step route</span>"
        )
        self.detail_label.setWordWrap(True)
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail_label.setContentsMargins(10, 10, 10, 10)
        self.detail_label.setTextFormat(Qt.TextFormat.RichText)

        scroll = QScrollArea()
        scroll.setWidget(self.detail_label)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #181825; border-radius: 6px;")
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row.addWidget(scroll)

        layout.addLayout(row)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_journeys(self, journeys):
        self.journeys = journeys
        self.table.setRowCount(len(journeys))

        bold = QFont()
        bold.setBold(True)

        for i, j in enumerate(journeys):
            modes = sorted({s.mode_of_transport for s in j.segments})

            # # column
            n = QTableWidgetItem(str(i + 1))
            n.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            n.setFont(bold)
            self.table.setItem(i, 0, n)

            # Time
            t = QTableWidgetItem(f"{j.total_duration} min")
            t.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, t)

            # Cost
            c = QTableWidgetItem(f"${j.total_cost:.2f}")
            c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, c)

            # Mode(s) — coloured by dominant mode
            icons = " ".join(MODE_ICONS.get(m, "") for m in modes)
            m_item = QTableWidgetItem(f"{icons}  {' + '.join(modes)}")
            m_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if modes:
                bg, fg = MODE_COLORS.get(modes[0], ("#45475a", "#cdd6f4"))
                m_item.setBackground(QColor(bg))
                m_item.setForeground(QColor(fg))
            self.table.setItem(i, 3, m_item)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(3, max(160, self.table.columnWidth(3)))

    def clear(self):
        self.journeys = []
        self.table.setRowCount(0)
        self.detail_label.setText(
            "<span style='color:#6c7086;'>← Select a journey to see its step-by-step route</span>"
        )

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_cell_clicked(self, row, _col):
        if 0 <= row < len(self.journeys):
            self.journeySelected.emit(row)
            self._show_details(row)

    def _show_details(self, index):
        if index < 0 or index >= len(self.journeys):
            return

        j = self.journeys[index]
        modes_used = sorted({s.mode_of_transport for s in j.segments})

        # ── Summary header ────────────────────────────────────────────────────
        mode_badges = "  ".join(
            f"<span style='background:{MODE_COLORS.get(m, ('#45475a','#cdd6f4'))[0]};"
            f"color:{MODE_COLORS.get(m, ('#45475a','#cdd6f4'))[1]};"
            f"padding:1px 7px; border-radius:4px; font-size:11px;'>"
            f"{MODE_ICONS.get(m,'')} {m}</span>"
            for m in modes_used
        )

        html = f"""
        <div style='font-family:Segoe UI,Arial,sans-serif; color:#cdd6f4;'>

          <div style='font-size:15px; font-weight:bold; margin-bottom:6px;'>
            Journey #{index + 1}
          </div>

          <table style='width:100%; border-collapse:collapse; margin-bottom:10px;'>
            <tr>
              <td style='padding:4px 10px 4px 0; color:#a6adc8; font-size:12px;'>Total time</td>
              <td style='padding:4px 0; font-size:13px; font-weight:bold; color:#89b4fa;'>
                {j.total_duration} min
              </td>
              <td style='padding:4px 10px 4px 16px; color:#a6adc8; font-size:12px;'>Total cost</td>
              <td style='padding:4px 0; font-size:13px; font-weight:bold; color:#a6e3a1;'>
                ${j.total_cost:.2f} HKD
              </td>
              <td style='padding:4px 10px 4px 16px; color:#a6adc8; font-size:12px;'>Segments</td>
              <td style='padding:4px 0; font-size:13px; font-weight:bold;'>
                {j.num_segments}
              </td>
            </tr>
          </table>

          <div style='margin-bottom:8px;'>{mode_badges}</div>

          <div style='border-top: 1px solid #313244; margin: 8px 0;'></div>

          <div style='font-size:12px; color:#a6adc8; margin-bottom:6px; font-weight:bold;'>
            STEP-BY-STEP ROUTE
          </div>
        """

        for k, seg in enumerate(j.segments):
            bg, fg = MODE_COLORS.get(seg.mode_of_transport, ("#45475a", "#cdd6f4"))
            icon = MODE_ICONS.get(seg.mode_of_transport, "")
            badge = (
                f"<span style='background:{bg}; color:{fg}; "
                f"padding:1px 6px; border-radius:3px; font-size:10px;'>"
                f"{icon} {seg.mode_of_transport}</span>"
            )

            # Alternating row shading
            row_bg = "#1e1e2e" if k % 2 == 0 else "#181825"

            html += f"""
          <div style='padding:5px 6px; background:{row_bg}; margin-bottom:2px; border-radius:4px;'>
            <span style='color:#6c7086; font-size:11px; margin-right:6px;'>{k+1}.</span>
            <b style='font-size:12px;'>{seg.from_stop}</b>
            <span style='color:#89b4fa; margin:0 5px;'>→</span>
            <b style='font-size:12px;'>{seg.to_stop}</b>
            <span style='float:right; font-size:11px; color:#a6adc8;'>
              {badge}&nbsp;&nbsp;{seg.duration} min&nbsp;&nbsp;${seg.cost:.2f}
            </span>
          </div>
            """

        html += "</div>"
        self.detail_label.setText(html)
        self.detail_label.adjustSize()
