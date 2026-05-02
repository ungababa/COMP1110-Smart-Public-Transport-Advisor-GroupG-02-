"""
Journey results table widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QScrollArea, QFrame, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QFont, QCursor


# ── Colour per transport mode ─────────────────────────────────────────────────
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

MODE_DARK_BG = {
    "MTR":             "#1a2035",
    "Bus":             "#1a2a1a",
    "Light Rail":      "#2a1e14",
    "Walk":            "#1e2028",
    "Airport Express": "#231a2e",
}

# Human-readable MTR line names (route_id prefix → display name)
MTR_LINE_NAMES = {
    "ISL": "Island Line",
    "TWL": "Tsuen Wan Line",
    "KTL": "Kwun Tong Line",
    "TML": "Tuen Ma Line",
    "EAL": "East Rail Line",
    "SIL": "South Island Line",
    "TCL": "Tung Chung Line",
    "AEL": "Airport Express",
    "DRL": "Disneyland Resort Line",
    "MOL": "Ma On Shan Line",
}


def _route_display_name(seg) -> str:
    """Return a human-readable name for the route of this segment."""
    mode = seg.mode_of_transport
    if mode == "Walk":
        return "Walk"
    if mode in ("MTR", "Light Rail", "Airport Express"):
        if seg.route_id:
            code = seg.route_id.split("_")[0]
            return MTR_LINE_NAMES.get(code, seg.route_id)
        return mode
    # Bus: use route_name if available
    if seg.route_name:
        return f"Bus {seg.route_name}"
    if seg.route_id:
        return f"Bus {seg.route_id}"
    return "Bus"


def _group_segments(segments):
    """Group consecutive segments that share the same route_id + mode into legs.

    Returns list of lists, where each inner list is one continuous leg.
    Segments with no route_id (e.g. Walk) are never merged.
    """
    if not segments:
        return []
    groups = []
    current = [segments[0]]
    for seg in segments[1:]:
        prev = current[-1]
        same_route = (
            seg.route_id is not None
            and seg.route_id == prev.route_id
            and seg.mode_of_transport == prev.mode_of_transport
        )
        if same_route:
            current.append(seg)
        else:
            groups.append(current)
            current = [seg]
    groups.append(current)
    return groups


# ── Clickable header frame ────────────────────────────────────────────────────

class _ClickableFrame(QFrame):
    """QFrame that emits clicked() on a left mouse press — used as leg header."""
    clicked = pyqtSignal()

    def __init__(self, base_bg: str, parent=None):
        super().__init__(parent)
        self._base_bg  = base_bg
        self._hover_bg = "#2a2a3e"
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_bg(self._base_bg)

    def _apply_bg(self, color: str):
        # Preserve the border-left set by the parent; only swap background-color
        cur = self.styleSheet()
        # Replace or set background-color inside existing sheet
        import re
        cur = re.sub(r'background-color\s*:[^;]+;', f'background-color: {color};', cur)
        if 'background-color' not in cur:
            cur = f"background-color: {color}; " + cur
        self.setStyleSheet(cur)

    def enterEvent(self, event):
        self._apply_bg(self._hover_bg)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_bg(self._base_bg)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ── Collapsible leg widget ────────────────────────────────────────────────────

class _LegWidget(QWidget):
    """One collapsible leg row: clickable header + hidden intermediate-stops panel."""

    def __init__(self, leg_segments, leg_index, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._setup(leg_segments, leg_index)

    def _setup(self, segs, idx):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 2)
        outer.setSpacing(0)

        mode        = segs[0].mode_of_transport
        route       = _route_display_name(segs[0])
        origin      = segs[0].from_stop
        dest        = segs[-1].to_stop
        total_dur   = sum(s.duration for s in segs)
        # Continuous same-route legs should show one journey fare,
        # not the sum of per-stop segment fares.
        if segs[0].route_id is not None:
            total_cost = segs[0].cost
        else:
            total_cost = sum(s.cost for s in segs)
        stops_count = len(segs) + 1          # stations touched (including endpoints)
        expandable  = stops_count > 2

        fg, _  = MODE_COLORS.get(mode, ("#a6adc8", "#1e1e2e"))
        dark   = MODE_DARK_BG.get(mode, "#1e1e2e")
        icon   = MODE_ICONS.get(mode, "")
        base_bg = '#1e1e2e' if idx % 2 == 0 else '#181825'

        # ── Header: clickable QFrame with QLabel children ─────────────────────
        self._header = _ClickableFrame(base_bg)
        self._header.setStyleSheet(
            f"background-color: {base_bg}; border: none; "
            f"border-left: 3px solid {fg};"
        )
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        h_layout = QHBoxLayout(self._header)
        h_layout.setContentsMargins(10, 7, 10, 7)
        h_layout.setSpacing(6)

        # Expand arrow (hidden if not expandable)
        self._arrow = QLabel("▸" if expandable else "")
        self._arrow.setStyleSheet("color: #6c7086; font-size: 10px; min-width: 10px;")
        self._arrow.setFixedWidth(12)
        h_layout.addWidget(self._arrow)

        # From → To  (plain text — no HTML needed)
        stops_lbl = QLabel(f"{origin}  →  {dest}")
        stops_lbl.setStyleSheet(
            "color: #cdd6f4; font-size: 12px; font-weight: 600; background: transparent;"
        )
        h_layout.addWidget(stops_lbl)

        h_layout.addStretch()

        # Mode badge: icon + route name
        mode_lbl = QLabel(f"{icon}  {route}")
        mode_lbl.setStyleSheet(
            f"color: {fg}; font-size: 10px; font-weight: 600; background: transparent;"
        )
        h_layout.addWidget(mode_lbl)

        # Time · Cost
        stats_lbl = QLabel(f"  {total_dur} min  ·  ${total_cost:.2f}")
        stats_lbl.setStyleSheet(
            "color: #6c7086; font-size: 11px; background: transparent;"
        )
        h_layout.addWidget(stats_lbl)

        if expandable:
            self._header.clicked.connect(self._toggle)

        outer.addWidget(self._header)

        # ── Intermediate stops panel (initially hidden) ───────────────────────
        self._detail_panel = QWidget()
        self._detail_panel.setVisible(False)
        self._detail_panel.setStyleSheet(
            f"background-color: {dark}; border-left: 3px solid {fg};"
        )
        detail_layout = QVBoxLayout(self._detail_panel)
        detail_layout.setContentsMargins(20, 4, 8, 4)
        detail_layout.setSpacing(1)

        for k, seg in enumerate(segs):
            stop_label = QLabel(
                f"<span style='color:#6c7086; font-size:10px;'>{k+1}.</span>  "
                f"<b style='color:#cdd6f4; font-size:11px;'>{seg.from_stop}</b>"
                f"<span style='color:#585b70; font-size:10px;'>  →  </span>"
                f"<b style='color:#cdd6f4; font-size:11px;'>{seg.to_stop}</b>"
                f"<span style='color:#6c7086; font-size:10px;'>"
                f"  {seg.duration} min  ·  ${seg.cost:.2f}</span>"
            )
            stop_label.setTextFormat(Qt.TextFormat.RichText)
            stop_label.setWordWrap(False)
            stop_label.setStyleSheet("padding: 3px 0;")
            detail_layout.addWidget(stop_label)

        outer.addWidget(self._detail_panel)

    def _toggle(self):
        self._expanded = not self._expanded
        self._detail_panel.setVisible(self._expanded)
        self._arrow.setText("▾" if self._expanded else "▸")


# ── Main results widget ───────────────────────────────────────────────────────

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

        # ── Detail panel — scrollable container of leg widgets ─────────────────
        self._detail_container = QWidget()
        self._detail_container.setStyleSheet("background-color: #181825;")
        self._detail_layout = QVBoxLayout(self._detail_container)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(0)
        self._detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._detail_container)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("background-color: #181825; border-radius: 6px;")
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row.addWidget(self._scroll)

        layout.addLayout(row)

        self._show_empty_state()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_journeys(self, journeys):
        self.journeys = journeys
        self.table.setRowCount(len(journeys))

        bold = QFont()
        bold.setBold(True)

        if journeys:
            min_time = min(j.total_duration for j in journeys)
            min_cost = min(j.total_cost      for j in journeys)

        for i, j in enumerate(journeys):
            modes = sorted({s.mode_of_transport for s in j.segments})

            n = QTableWidgetItem(str(i + 1))
            n.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            n.setFont(bold)
            self.table.setItem(i, 0, n)

            t = QTableWidgetItem(f"{j.total_duration} min")
            t.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j.total_duration == min_time:
                t.setForeground(QColor("#89b4fa"))
            self.table.setItem(i, 1, t)

            c = QTableWidgetItem(f"${j.total_cost:.2f}")
            c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j.total_cost == min_cost:
                c.setForeground(QColor("#a6e3a1"))
            self.table.setItem(i, 2, c)

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

    def _clear_detail_panel(self):
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_empty_state(self):
        self._clear_detail_panel()
        lbl = QLabel(
            "<div style='font-family: Segoe UI, Arial, sans-serif; "
            "color: #45475a; text-align: center; padding: 40px 20px;'>"
            "<div style='font-size: 13px; font-weight: 600; color: #585b70; "
            "margin-bottom: 8px;'>No journey selected</div>"
            "<div style='font-size: 11px; line-height: 1.8; color: #45475a;'>"
            "Enter an origin and destination,<br>"
            "then click <b style='color: #6c7086;'>Find Journeys</b>.<br><br>"
            "Select a result row to see<br>the step-by-step route here."
            "</div></div>"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        lbl.setWordWrap(True)
        self._detail_layout.addWidget(lbl)

    def _show_details(self, index: int):
        if index < 0 or index >= len(self.journeys):
            return

        j = self.journeys[index]
        self._clear_detail_panel()

        # ── Summary bar ───────────────────────────────────────────────────────
        modes_used = sorted({s.mode_of_transport for s in j.segments})
        mode_badges = "  ".join(
            f"<span style='background:{MODE_DARK_BG.get(m,'#313244')};"
            f"color:{MODE_COLORS.get(m,('#a6adc8',''))[0]};"
            f"border:1px solid {MODE_COLORS.get(m,('#45475a',''))[0]};"
            f"padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;'>"
            f"{MODE_ICONS.get(m,'')} {m}</span>"
            for m in modes_used
        )

        summary = QLabel(
            f"<div style='font-family:Segoe UI,Arial,sans-serif; padding:10px 12px;'>"
            f"<div style='font-size:14px;font-weight:700;color:#cdd6f4;"
            f"margin-bottom:8px;'>Journey #{index+1}</div>"
            f"<table style='border-collapse:collapse;margin-bottom:10px;'><tr>"
            f"<td style='color:#6c7086;font-size:10px;font-weight:700;"
            f"letter-spacing:0.8px;padding-right:12px;'>TIME</td>"
            f"<td style='font-size:13px;font-weight:700;color:#89b4fa;"
            f"padding-right:20px;'>{j.total_duration} min</td>"
            f"<td style='color:#6c7086;font-size:10px;font-weight:700;"
            f"letter-spacing:0.8px;padding-right:12px;'>COST</td>"
            f"<td style='font-size:13px;font-weight:700;color:#a6e3a1;"
            f"padding-right:20px;'>${j.total_cost:.2f}</td>"
            f"<td style='color:#6c7086;font-size:10px;font-weight:700;"
            f"letter-spacing:0.8px;padding-right:12px;'>LEGS</td>"
            f"<td style='font-size:13px;font-weight:700;color:#cdd6f4;'>"
            f"{len(_group_segments(j.segments))}</td>"
            f"</tr></table>"
            f"<div style='margin-bottom:4px;'>{mode_badges}</div>"
            f"</div>"
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        summary.setWordWrap(True)
        self._detail_layout.addWidget(summary)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("border: none; border-top: 1px solid #313244; margin: 0 8px;")
        self._detail_layout.addWidget(div)

        # Section label
        sec = QLabel("STEP-BY-STEP ROUTE  ·  click a leg to expand")
        sec.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #45475a; "
            "letter-spacing: 1px; padding: 6px 12px 4px 12px;"
        )
        self._detail_layout.addWidget(sec)

        # ── One LegWidget per grouped leg ─────────────────────────────────────
        legs = _group_segments(j.segments)
        for i, leg in enumerate(legs):
            self._detail_layout.addWidget(_LegWidget(leg, i))
            # Add buffer time label between legs (transfers)
            if i < len(legs) - 1:
                buffer_label = QLabel("⏱️ Transfer buffer: 5 min")
                buffer_label.setStyleSheet(
                    "color: #f38ba8; font-size: 10px; font-weight: 600; "
                    "padding: 4px 12px; background-color: #1e1e2e; border-radius: 4px; "
                    "margin: 2px 0;"
                )
                self._detail_layout.addWidget(buffer_label)

        # Spacer at bottom
        self._detail_layout.addStretch()
