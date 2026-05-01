"""
Journey input form widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

from .widgets import AutocompleteComboBox


# ── Mode definitions ──────────────────────────────────────────────────────────

MODES = [
    ("MTR",             "🚇 MTR",             "#89b4fa", "#1a2035"),
    ("Bus",             "🚌 Bus",             "#a6e3a1", "#1a2a1a"),
    ("Light Rail",      "🚊 Light Rail",      "#fab387", "#2a1e14"),
    ("Walk",            "🚶 Walk",            "#a6adc8", "#1e2028"),
    ("Airport Express", "✈️ Airport Exp.",    "#cba6f7", "#231a2e"),
]

PREFS = [
    ("fastest",  "Fastest"),
    ("cheapest", "Cheapest"),
    ("fewest",   "Fewest"),
]


class JourneyForm(QWidget):
    """Left-panel widget for entering journey query parameters."""

    searchRequested = pyqtSignal(dict)

    def __init__(self, stops, parent=None):
        super().__init__(parent)
        self.stops = sorted(stops) if stops else []
        self._mode_btns: dict[str, tuple[QPushButton, str, str]] = {}  # key → (btn, color, dark_bg)
        self._pref_btns: dict[str, QPushButton] = {}
        self._current_pref = "fastest"
        self._setup_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(14, 14, 14, 14)

        # ── App header ───────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        icon_lbl = QLabel("🚌")
        icon_lbl.setStyleSheet("font-size: 24px; padding: 0;")
        icon_lbl.setFixedWidth(32)
        header_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        app_name = QLabel("Transport Advisor")
        app_name.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #cdd6f4; "
            "letter-spacing: 0.3px; padding: 0;"
        )
        sub_lbl = QLabel("Hong Kong  ·  Smart Routes")
        sub_lbl.setStyleSheet(
            "font-size: 10px; color: #6c7086; letter-spacing: 0.5px; padding: 0;"
        )
        title_col.addWidget(app_name)
        title_col.addWidget(sub_lbl)
        header_row.addLayout(title_col)
        header_row.addStretch()
        layout.addLayout(header_row)

        layout.addSpacing(14)
        self._divider(layout)
        layout.addSpacing(14)

        # ── FROM ─────────────────────────────────────────────────────────────
        layout.addWidget(self._cap_label("FROM"))
        layout.addSpacing(5)
        self.origin_combo = AutocompleteComboBox()
        self.origin_combo.setPlaceholderText("Origin station…")
        layout.addWidget(self.origin_combo)

        layout.addSpacing(6)

        # ── Swap button (small circle between fields) ─────────────────────────
        swap_row = QHBoxLayout()
        swap_row.addStretch()
        swap_btn = QPushButton("⇅")
        swap_btn.setToolTip("Swap origin and destination")
        swap_btn.setFixedSize(30, 30)
        swap_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                border-radius: 15px;
                font-size: 15px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton:hover   { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
        """)
        swap_btn.clicked.connect(self._swap_stops)
        swap_row.addWidget(swap_btn)
        swap_row.addStretch()
        layout.addLayout(swap_row)
        layout.addSpacing(6)

        # ── TO ───────────────────────────────────────────────────────────────
        layout.addWidget(self._cap_label("TO"))
        layout.addSpacing(5)
        self.dest_combo = AutocompleteComboBox()
        self.dest_combo.setPlaceholderText("Destination station…")
        layout.addWidget(self.dest_combo)

        layout.addSpacing(16)
        self._divider(layout)
        layout.addSpacing(14)

        # ── Preference: segmented toggle ──────────────────────────────────────
        layout.addWidget(self._cap_label("PREFERENCE"))
        layout.addSpacing(8)

        pref_row = QHBoxLayout()
        pref_row.setSpacing(4)
        for key, label in PREFS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(self._pref_style(active=(key == "fastest")))
            btn.clicked.connect(lambda _, k=key: self._on_pref_clicked(k))
            self._pref_btns[key] = btn
            pref_row.addWidget(btn)
        self._pref_btns["fastest"].setChecked(True)
        layout.addLayout(pref_row)

        layout.addSpacing(16)
        self._divider(layout)
        layout.addSpacing(14)

        # ── Transport modes: pill toggle buttons ──────────────────────────────
        layout.addWidget(self._cap_label("TRANSPORT MODES"))
        layout.addSpacing(8)

        # 2-per-row grid, last row left-aligned
        mode_rows = [MODES[0:2], MODES[2:4], MODES[4:5]]
        for row_modes in mode_rows:
            row = QHBoxLayout()
            row.setSpacing(6)
            for key, label, color, dark_bg in row_modes:
                btn = QPushButton(label)
                btn.setCheckable(True)
                btn.setChecked(True)
                btn.setStyleSheet(self._mode_style(color, dark_bg, active=True))
                btn.clicked.connect(
                    lambda _, k=key: self._on_mode_toggled(k)
                )
                self._mode_btns[key] = (btn, color, dark_bg)
                row.addWidget(btn)
            if len(row_modes) == 1:
                row.addStretch()
            layout.addLayout(row)
            layout.addSpacing(5)

        layout.addSpacing(14)
        self._divider(layout)
        layout.addSpacing(14)

        # ── Find Journeys ─────────────────────────────────────────────────────
        self.search_btn = QPushButton("Find Journeys")
        self.search_btn.setDefault(True)
        self.search_btn.setMinimumHeight(44)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }
            QPushButton:hover    { background-color: #b4befe; }
            QPushButton:pressed  { background-color: #74c7ec; }
            QPushButton:disabled { background-color: #313244; color: #6c7086; }
        """)
        self.search_btn.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_btn)

        layout.addStretch()

        # ── Quiet tip at the very bottom ──────────────────────────────────────
        tip = QLabel("Click any station on the map to set origin or destination")
        tip.setWordWrap(True)
        tip.setStyleSheet(
            "font-size: 10px; color: #45475a; padding: 6px 0 0 0; line-height: 1.4;"
        )
        layout.addWidget(tip)

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _cap_label(text: str) -> QLabel:
        """Small all-caps section label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #6c7086; "
            "letter-spacing: 1.2px; padding: 0;"
        )
        return lbl

    @staticmethod
    def _divider(layout: QVBoxLayout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: none; border-top: 1px solid #313244;")
        line.setFixedHeight(1)
        layout.addWidget(line)

    @staticmethod
    def _pref_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 6px 2px;
                }
            """
        return """
            QPushButton {
                background-color: #313244;
                color: #a6adc8;
                border: 1px solid #45475a;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
                padding: 6px 2px;
            }
            QPushButton:hover { background-color: #3d3f55; color: #cdd6f4; }
        """

    @staticmethod
    def _mode_style(color: str, dark_bg: str, active: bool) -> str:
        if active:
            return f"""
                QPushButton {{
                    background-color: {dark_bg};
                    color: {color};
                    border: 1.5px solid {color};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 5px 6px;
                }}
                QPushButton:hover {{ background-color: {dark_bg}; border-color: {color}; }}
            """
        return """
            QPushButton {
                background-color: #1e1e2e;
                color: #45475a;
                border: 1.5px solid #313244;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 500;
                padding: 5px 6px;
            }
            QPushButton:hover { background-color: #313244; color: #6c7086; }
        """

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_pref_clicked(self, key: str):
        self._current_pref = key
        for k, btn in self._pref_btns.items():
            btn.setChecked(k == key)
            btn.setStyleSheet(self._pref_style(active=(k == key)))

    def _on_mode_toggled(self, key: str):
        btn, color, dark_bg = self._mode_btns[key]
        btn.setStyleSheet(self._mode_style(color, dark_bg, active=btn.isChecked()))

    def _swap_stops(self):
        origin = self.origin_combo.currentText()
        dest   = self.dest_combo.currentText()
        self.origin_combo.setEditText(dest)
        self.dest_combo.setEditText(origin)

    def _on_search_clicked(self):
        origin      = self.origin_combo.get_current_text()
        destination = self.dest_combo.get_current_text()
        modes       = [k for k, (btn, _, __) in self._mode_btns.items() if btn.isChecked()]

        self.searchRequested.emit({
            "origin":      origin,
            "destination": destination,
            "preference":  self._current_pref,
            "modes":       modes,
        })

    # ── Public API ────────────────────────────────────────────────────────────

    def populate_stops(self, stops):
        """Populate both comboboxes with all available stops."""
        self.stops = sorted(stops)
        self.origin_combo.set_items(self.stops)
        self.dest_combo.set_items(self.stops)

    def set_origin(self, name: str):
        self.origin_combo.setEditText(name)

    def set_destination(self, name: str):
        self.dest_combo.setEditText(name)
