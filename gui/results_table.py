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

# Dark tinted background per mode (for badges/pills)
MODE_DARK_BG = {
    "MTR":             "#1a2035",
    "Bus":             "#1a2a1a",
    "Light Rail":      "#2a1e14",
    "Walk":            "#1e2028",
    "Airport Express": "#231a2e",
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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ── Header row ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header = QLabel("Journey Results")
        header.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #cdd6f4; padding: 2px 0;"
        )
        header_row.addWidget(header)
        header_row.addStretch()
        self._count_label = QLabel("")
        self._count_label.setStyleSheet("font-size: 11px; color: #6c7086; padding: 2px 0;")
        header_row.addWidget(self._count_label)
        layout.addLayout(header_row)

        # ── Horizontal split: table left, detail panel right ──────────────────
        row = QHBoxLayout()
        row.setSpacing(8)

        # ── Table ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Time", "Cost", "Mode(s)"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumWidth(320)
        self.table.setMaximumWidth(400)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.table.cellClicked.connect(self._on_cell_clicked)
        row.addWidget(self.table)

        # ── Detail panel — scrollable ─────────────────────────────────────────
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail_label.setContentsMargins(12, 12, 12, 12)
        self.detail_label.setTextFormat(Qt.TextFormat.RichText)
        self._show_empty_state()

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

        # Determine best journey in each category for highlighting
        if journeys:
            min_time = min(j.total_duration for j in journeys)
            min_cost = min(j.total_cost for j in journeys)

        for i, j in enumerate(journeys):
            modes = sorted({s.mode_of_transport for s in j.segments})

            # # column
            n = QTableWidgetItem(str(i + 1))
            n.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            n.setFont(bold)
            self.table.setItem(i, 0, n)

            # Time — highlight best with color only (no emoji)
            t = QTableWidgetItem(f"{j.total_duration} min")
            t.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j.total_duration == min_time:
                t.setForeground(QColor("#89b4fa"))
            self.table.setItem(i, 1, t)

            # Cost — highlight best with color only
            c = QTableWidgetItem(f"${j.total_cost:.2f}")
            c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j.total_cost == min_cost:
                c.setForeground(QColor("#a6e3a1"))
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

        n = len(journeys)
        self._count_label.setText(f"{n} route{'s' if n != 1 else ''} found")

    def clear(self):
        self.journeys = []
        self.table.setRowCount(0)
        self._count_label.setText("")
        self._show_empty_state()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_cell_clicked(self, row, _col):
        if 0 <= row < len(self.journeys):
            self.journeySelected.emit(row)
            self._show_details(row)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _show_empty_state(self):
        self.detail_label.setText("""
        <div style='font-family: Segoe UI, Arial, sans-serif;
                    color: #45475a;
                    text-align: center;
                    padding: 40px 20px;'>
          <div style='font-size: 13px; font-weight: 600; color: #585b70;
                      margin-bottom: 8px;'>
            No journey selected
          </div>
          <div style='font-size: 11px; line-height: 1.8; color: #45475a;'>
            Enter an origin and destination,<br>
            then click <b style='color: #6c7086;'>Find Journeys</b>.<br><br>
            Select a result row to see<br>the step-by-step route here.
          </div>
        </div>
        """)

    def _show_details(self, index: int):
        if index < 0 or index >= len(self.journeys):
            return

        j = self.journeys[index]
        modes_used = sorted({s.mode_of_transport for s in j.segments})

        # ── Mode badges ───────────────────────────────────────────────────────
        mode_badges = "&nbsp;&nbsp;".join(
            f"<span style='"
            f"background:{MODE_DARK_BG.get(m, '#313244')};"
            f"color:{MODE_COLORS.get(m, ('#a6adc8','#1e1e2e'))[0]};"
            f"border:1px solid {MODE_COLORS.get(m, ('#45475a','#cdd6f4'))[0]};"
            f"padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;'>"
            f"{MODE_ICONS.get(m,'')} {m}</span>"
            for m in modes_used
        )

        # ── Summary stats using table (reliable in Qt HTML) ───────────────────
        html = f"""
        <div style='font-family: Segoe UI, Arial, sans-serif; color: #cdd6f4;'>

          <div style='font-size: 15px; font-weight: 700; color: #cdd6f4;
                      margin-bottom: 10px;'>
            Journey #{index + 1}
          </div>

          <table style='border-collapse: collapse; margin-bottom: 12px;'>
            <tr>
              <td style='padding: 3px 16px 3px 0; color: #6c7086;
                         font-size: 11px; font-weight: 600; letter-spacing: 0.8px;'>
                TIME
              </td>
              <td style='padding: 3px 24px 3px 0; font-size: 14px;
                         font-weight: 700; color: #89b4fa;'>
                {j.total_duration} min
              </td>
              <td style='padding: 3px 16px 3px 0; color: #6c7086;
                         font-size: 11px; font-weight: 600; letter-spacing: 0.8px;'>
                COST
              </td>
              <td style='padding: 3px 24px 3px 0; font-size: 14px;
                         font-weight: 700; color: #a6e3a1;'>
                ${j.total_cost:.2f}
              </td>
              <td style='padding: 3px 16px 3px 0; color: #6c7086;
                         font-size: 11px; font-weight: 600; letter-spacing: 0.8px;'>
                LEGS
              </td>
              <td style='padding: 3px 0; font-size: 14px; font-weight: 700;
                         color: #cdd6f4;'>
                {j.num_segments}
              </td>
            </tr>
          </table>

          <div style='margin-bottom: 12px;'>{mode_badges}</div>

          <div style='border-top: 1px solid #313244; margin-bottom: 10px;'></div>

          <div style='font-size: 10px; font-weight: 700; color: #6c7086;
                      letter-spacing: 1.2px; margin-bottom: 8px;'>
            STEP-BY-STEP ROUTE
          </div>
        """

        for k, seg in enumerate(j.segments):
            fg_color, _ = MODE_COLORS.get(seg.mode_of_transport, ("#a6adc8", "#1e1e2e"))
            dark_bg     = MODE_DARK_BG.get(seg.mode_of_transport, "#313244")
            icon        = MODE_ICONS.get(seg.mode_of_transport, "")

            # Badge for this segment's mode
            badge = (
                f"<span style='background:{dark_bg}; color:{fg_color}; "
                f"border:1px solid {fg_color}; "
                f"padding:1px 6px; border-radius:4px; font-size:10px; font-weight:600;'>"
                f"{icon} {seg.mode_of_transport}</span>"
            )

            row_bg = "#1e1e2e" if k % 2 == 0 else "#181825"

            # Use a table row for correct right-alignment (float:right unsupported in Qt)
            html += f"""
          <div style='background:{row_bg}; margin-bottom:3px;
                      border-radius:5px; padding:6px 8px;'>
            <table style='width:100%; border-collapse:collapse;'>
              <tr>
                <td style='width:18px; color:#585b70; font-size:11px;
                           vertical-align:middle; padding-right:6px;'>
                  {k + 1}.
                </td>
                <td style='vertical-align:middle;'>
                  <span style='font-size:12px; font-weight:700;
                               color:#cdd6f4;'>{seg.from_stop}</span>
                  <span style='color:#89b4fa; margin:0 5px;
                               font-size:12px;'>→</span>
                  <span style='font-size:12px; font-weight:700;
                               color:#cdd6f4;'>{seg.to_stop}</span>
                </td>
                <td style='text-align:right; white-space:nowrap;
                           vertical-align:middle; padding-left:8px;'>
                  {badge}
                  <span style='font-size:11px; color:#a6adc8;
                               margin-left:6px;'>{seg.duration} min</span>
                  <span style='font-size:11px; color:#a6e3a1;
                               margin-left:4px;'>${seg.cost:.2f}</span>
                </td>
              </tr>
            </table>
          </div>
            """

        html += "</div>"
        self.detail_label.setText(html)
        self.detail_label.adjustSize()
