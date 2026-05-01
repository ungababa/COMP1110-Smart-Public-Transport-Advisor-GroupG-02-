"""
Journey input form widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from .widgets import AutocompleteComboBox


class JourneyForm(QWidget):
    """Widget for entering journey query parameters."""

    searchRequested = pyqtSignal(dict)

    def __init__(self, stops, parent=None):
        super().__init__(parent)
        self.stops = sorted(stops) if stops else []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel("Find a Journey")
        title.setStyleSheet("font-size: 17px; font-weight: bold; padding-bottom: 4px;")
        layout.addWidget(title)

        hint = QLabel("Tip: Click any station on the map\nto set it as origin or destination.")
        hint.setStyleSheet("font-size: 11px; color: #a6adc8;")
        layout.addWidget(hint)

        layout.addSpacing(4)

        # ── Origin ──────────────────────────────────────────────────────────
        layout.addWidget(QLabel("From:"))
        self.origin_combo = AutocompleteComboBox()
        layout.addWidget(self.origin_combo)

        # ── Swap button ──────────────────────────────────────────────────────
        swap_btn = QPushButton("⇅  Swap")
        swap_btn.setToolTip("Swap origin and destination")
        swap_btn.clicked.connect(self._swap_stops)
        layout.addWidget(swap_btn)

        # ── Destination ──────────────────────────────────────────────────────
        layout.addWidget(QLabel("To:"))
        self.dest_combo = AutocompleteComboBox()
        layout.addWidget(self.dest_combo)

        layout.addSpacing(6)

        # ── Preference ───────────────────────────────────────────────────────
        pref_group = QGroupBox("Ranking Preference")
        pref_layout = QVBoxLayout()
        self.pref_combo = QComboBox()
        self.pref_combo.addItems(["Fastest", "Cheapest", "Fewest Segments"])
        pref_layout.addWidget(self.pref_combo)
        pref_group.setLayout(pref_layout)
        layout.addWidget(pref_group)

        # ── Transport modes ──────────────────────────────────────────────────
        mode_group = QGroupBox("Transport Modes")
        mode_layout = QVBoxLayout()

        self.mtr_check       = QCheckBox("🔵  MTR")
        self.bus_check        = QCheckBox("🟢  Bus")
        self.light_rail_check = QCheckBox("🟠  Light Rail")
        self.walk_check       = QCheckBox("⚫  Walk")
        self.airport_check    = QCheckBox("🟣  Airport Express")

        for cb in (self.mtr_check, self.bus_check, self.light_rail_check,
                   self.walk_check, self.airport_check):
            cb.setChecked(True)
            mode_layout.addWidget(cb)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ── Search button ────────────────────────────────────────────────────
        self.search_btn = QPushButton("🔍  Find Journeys")
        self.search_btn.setDefault(True)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_btn)

        layout.addStretch()

    def _swap_stops(self):
        """Swap origin and destination."""
        origin = self.origin_combo.currentText()
        dest   = self.dest_combo.currentText()
        self.origin_combo.setEditText(dest)
        self.dest_combo.setEditText(origin)

    def _on_search_clicked(self):
        origin      = self.origin_combo.get_current_text()
        destination = self.dest_combo.get_current_text()

        pref_map = {
            "Fastest":        "fastest",
            "Cheapest":       "cheapest",
            "Fewest Segments": "fewest",
        }
        preference = pref_map.get(self.pref_combo.currentText(), "fastest")

        modes = []
        if self.mtr_check.isChecked():        modes.append("MTR")
        if self.bus_check.isChecked():         modes.append("Bus")
        if self.light_rail_check.isChecked(): modes.append("Light Rail")
        if self.walk_check.isChecked():        modes.append("Walk")
        if self.airport_check.isChecked():    modes.append("Airport Express")

        self.searchRequested.emit({
            "origin":      origin,
            "destination": destination,
            "preference":  preference,
            "modes":       modes,
        })

    def populate_stops(self, stops):
        """Populate both comboboxes with all available stops."""
        self.stops = sorted(stops)
        self.origin_combo.set_items(self.stops)
        self.dest_combo.set_items(self.stops)

    def set_origin(self, name: str):
        """Set origin from external source (e.g. map click)."""
        self.origin_combo.setEditText(name)

    def set_destination(self, name: str):
        """Set destination from external source (e.g. map click)."""
        self.dest_combo.setEditText(name)
