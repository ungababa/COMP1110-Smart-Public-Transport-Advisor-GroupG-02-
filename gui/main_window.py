"""
Main GUI window for Smart Public Transport Advisor — Improved
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QSplitter,
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal

from .hkmap import HKMapWidget
from .journey_form import JourneyForm
from .results_table import ResultsTable


# ── Background worker ─────────────────────────────────────────────────────────

class _JourneyWorker(QObject):
    """Runs the BFS journey search on a background thread so the UI never freezes."""

    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, network, fare_lookup, origin, destination, preference, modes):
        super().__init__()
        self.network     = network
        self.fare_lookup = fare_lookup
        self.origin      = origin
        self.destination = destination
        self.preference  = preference
        self.modes       = modes

    def run(self):
        try:
            from main import generate_journeys, rank_journeys, filter_journeys_by_transport
            journeys = generate_journeys(
                self.network, self.fare_lookup,
                self.origin, self.destination,
            )
            if self.modes:
                journeys = filter_journeys_by_transport(journeys, set(self.modes))
            journeys = rank_journeys(journeys, self.preference)[:10]
            self.finished.emit(journeys)
        except Exception as exc:
            self.error.emit(str(exc))


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, network, fare_lookup):
        super().__init__()
        self.network        = network
        self.fare_lookup    = fare_lookup
        self.found_journeys = []
        self._thread        = None
        self._worker        = None
        self._setup_ui()
        self._apply_dark_theme()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setWindowTitle("Smart Public Transport Advisor")
        self.setGeometry(80, 80, 1650, 960)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # ── Left: Journey Form ────────────────────────────────────────────────
        self.form = JourneyForm(self.network.all_stops)
        self.form.populate_stops(self.network.all_stops)
        self.form.setFixedWidth(300)
        self.form.searchRequested.connect(self._on_search_requested)

        # ── Right: vertical splitter (map on top, results table below) ────────
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self.map_widget = HKMapWidget()
        self.map_widget.set_network(self.network)
        self.map_widget.stationClicked.connect(self._on_station_clicked)

        self.results_table = ResultsTable()
        self.results_table.journeySelected.connect(self._on_journey_selected)
        self.results_table.setMinimumHeight(220)

        right_splitter.addWidget(self.map_widget)
        right_splitter.addWidget(self.results_table)
        right_splitter.setSizes([680, 260])

        # ── Horizontal splitter: form | (map + results) ───────────────────────
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.addWidget(self.form)
        h_splitter.addWidget(right_splitter)
        h_splitter.setSizes([300, 1350])
        root_layout.addWidget(h_splitter)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        stops   = len(self.network.all_stops)
        segs    = self.network.get_num_segments()
        self.status_bar.showMessage(
            f"Network loaded  ·  {stops} stops  ·  {segs} segments  ·  "
            "Enter an origin & destination, then click Find Journeys"
        )

        self._searching_label = QLabel("  🔍 Searching…")
        self._searching_label.setVisible(False)
        self.status_bar.addPermanentWidget(self._searching_label)

    # ── Signals & slots ───────────────────────────────────────────────────────

    def _on_station_clicked(self, station_name: str):
        """
        When the user clicks a dot on the map, fill origin first, then
        destination if origin is already set.
        """
        origin = self.form.origin_combo.currentText().strip()
        dest   = self.form.dest_combo.currentText().strip()

        if not origin:
            self.form.set_origin(station_name)
            self.status_bar.showMessage(f"Origin set to: {station_name}")
        elif not dest or dest == origin:
            self.form.set_destination(station_name)
            self.status_bar.showMessage(f"Destination set to: {station_name}")
        else:
            # Both already set — re-set origin (start fresh cycle)
            self.form.set_origin(station_name)
            self.form.set_destination("")
            self.status_bar.showMessage(f"Origin reset to: {station_name}  ·  Now pick a destination")

    def _on_search_requested(self, params: dict):
        origin      = params["origin"]
        destination = params["destination"]
        preference  = params["preference"]
        modes       = params["modes"]

        # ── Validate inputs ───────────────────────────────────────────────────
        if not origin:
            self._set_status("Please enter an origin stop.", error=True)
            return
        if not destination:
            self._set_status("Please enter a destination stop.", error=True)
            return
        if origin not in self.network.all_stops:
            self._set_status(f"Origin '{origin}' not found in the network.", error=True)
            return
        if destination not in self.network.all_stops:
            self._set_status(f"Destination '{destination}' not found in the network.", error=True)
            return
        if origin == destination:
            self._set_status("Origin and destination must be different.", error=True)
            return

        # ── Prepare UI for search ─────────────────────────────────────────────
        self.form.search_btn.setEnabled(False)
        self._searching_label.setVisible(True)
        self.results_table.clear()
        self.map_widget.clear_highlight()
        self._set_status(
            f"Searching {preference}  route:  {origin}  →  {destination} …"
        )

        # ── Kick off background thread ────────────────────────────────────────
        self._thread = QThread()
        self._worker = _JourneyWorker(
            self.network, self.fare_lookup,
            origin, destination, preference, modes,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.error.connect(self._on_search_error)
        # Clean up thread after it's done
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_search_finished(self, journeys: list):
        self.form.search_btn.setEnabled(True)
        self._searching_label.setVisible(False)
        self.found_journeys = journeys

        if not journeys:
            self._set_status("No journeys found for this query — try relaxing the transport mode filters.")
            return

        self.results_table.set_journeys(journeys)
        # Auto-select and show the first (best) journey
        self._on_journey_selected(0)
        self._set_status(
            f"Found {len(journeys)} journey(s)  ·  "
            "Click a row in the table below to highlight it on the map"
        )

    def _on_search_error(self, msg: str):
        self.form.search_btn.setEnabled(True)
        self._searching_label.setVisible(False)
        self._set_status(f"Search error: {msg}", error=True)

    def _on_journey_selected(self, index: int):
        if 0 <= index < len(self.found_journeys):
            self.map_widget.highlight_journey(self.found_journeys[index])
            self.results_table.table.selectRow(index)
            self.results_table._show_detail(index)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, error: bool = False):
        self.status_bar.showMessage(msg)
        color = "#f38ba8" if error else "#a6adc8"
        self.status_bar.setStyleSheet(f"color: {color};")

    # ── Styling ───────────────────────────────────────────────────────────────

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 13px;
            }

            /* ── Buttons ── */
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton:hover   { background-color: #b4befe; }
            QPushButton:pressed { background-color: #74c7ec; }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }

            /* ── Inputs ── */
            QLineEdit, QComboBox {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 5px 10px;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #89b4fa; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }

            /* ── Group boxes ── */
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 6px;
            }
            QGroupBox::title {
                color: #89b4fa;
                subcontrol-origin: margin;
                left: 10px;
                font-weight: bold;
            }

            /* ── Check boxes ── */
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 2px solid #6c7086;
                border-radius: 4px;
                background: #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }

            /* ── Table ── */
            QTableWidget {
                background-color: #181825;
                alternate-background-color: #1e1e2e;
                gridline-color: #313244;
                border: none;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 6px 8px;
                border: none;
                font-weight: bold;
            }

            /* ── Splitters ── */
            QSplitter::handle { background-color: #45475a; }

            /* ── Scroll bars ── */
            QScrollBar:vertical {
                background: #181825; width: 10px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #45475a; border-radius: 5px; min-height: 20px;
            }
            QScrollBar:horizontal {
                background: #181825; height: 10px; margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #45475a; border-radius: 5px; min-width: 20px;
            }
            QScrollBar::add-line, QScrollBar::sub-line { background: none; }

            /* ── Status bar ── */
            QStatusBar {
                background-color: #181825;
                color: #a6adc8;
                border-top: 1px solid #313244;
            }

            /* ── Tooltips ── */
            QToolTip {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #89b4fa;
                padding: 4px 8px;
                border-radius: 4px;
            }
        """)


# ── Entry point ───────────────────────────────────────────────────────────────

def run_gui(network, fare_lookup):
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(network, fare_lookup)
    window.show()
    sys.exit(app.exec())
