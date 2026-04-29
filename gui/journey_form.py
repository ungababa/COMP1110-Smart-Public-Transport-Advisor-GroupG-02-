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

    # Signal emitted when user requests journey search
    searchRequested = pyqtSignal(dict)

    def __init__(self, stops, parent=None):
        super().__init__(parent)
        self.stops = list(stops) if stops else []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Find a Journey")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Origin input
        origin_layout = QHBoxLayout()
        origin_layout.addWidget(QLabel("From:"))
        self.origin_combo = AutocompleteComboBox()
        # Don't preload all stops - will be set when user clicks
        origin_layout.addWidget(self.origin_combo)
        layout.addLayout(origin_layout)

        # Destination input
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("To:"))
        self.dest_combo = AutocompleteComboBox()
        # Don't preload all stops - will be set when user clicks
        dest_layout.addWidget(self.dest_combo)
        layout.addLayout(dest_layout)

        # Separator
        layout.addSpacing(10)

        # Preference selection
        pref_group = QGroupBox("Ranking Preference")
        pref_layout = QVBoxLayout()

        self.pref_combo = QComboBox()
        self.pref_combo.addItems(["Fastest", "Cheapest", "Fewest Segments"])
        pref_layout.addWidget(self.pref_combo)
        pref_group.setLayout(pref_layout)
        layout.addWidget(pref_group)

        # Transport modes
        mode_group = QGroupBox("Transport Modes")
        mode_layout = QVBoxLayout()

        self.mtr_check = QCheckBox("MTR")
        self.mtr_check.setChecked(True)
        mode_layout.addWidget(self.mtr_check)

        self.bus_check = QCheckBox("Bus")
        self.bus_check.setChecked(True)
        mode_layout.addWidget(self.bus_check)

        self.light_rail_check = QCheckBox("Light Rail")
        self.light_rail_check.setChecked(True)
        mode_layout.addWidget(self.light_rail_check)

        self.walk_check = QCheckBox("Walk")
        self.walk_check.setChecked(True)
        mode_layout.addWidget(self.walk_check)

        self.airport_check = QCheckBox("Airport Express")
        self.airport_check.setChecked(True)
        mode_layout.addWidget(self.airport_check)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Search button
        self.search_btn = QPushButton("Find Journeys")
        self.search_btn.setDefault(True)
        self.search_btn.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_btn)

        layout.addStretch()

    def _on_search_clicked(self):
        """Handle search button click."""
        origin = self.origin_combo.get_current_text()
        destination = self.dest_combo.get_current_text()

        # Get preference
        pref_map = {"Fastest": "fastest", "Cheapest": "cheapest", "Fewest Segments": "fewest"}
        preference = pref_map.get(self.pref_combo.currentText(), "fastest")

        # Get transport modes
        modes = []
        if self.mtr_check.isChecked():
            modes.append("MTR")
        if self.bus_check.isChecked():
            modes.append("Bus")
        if self.light_rail_check.isChecked():
            modes.append("Light Rail")
        if self.walk_check.isChecked():
            modes.append("Walk")
        if self.airport_check.isChecked():
            modes.append("Airport Express")

        params = {
            "origin": origin,
            "destination": destination,
            "preference": preference,
            "modes": modes
        }
        self.searchRequested.emit(params)

    def populate_stops(self, stops):
        """Populate the stop comboboxes with all available stops."""
        self.stops = sorted(stops)
        self.origin_combo.set_items(self.stops[:500])  # Limit to 500 for performance
        self.dest_combo.set_items(self.stops[:500])

    def update_stops(self, stops):
        """Update the available stops list."""
        self.stops = sorted(stops)
        self.origin_combo.set_items(self.stops)
        self.dest_combo.set_items(self.stops)