"""
Main GUI window for Smart Public Transport Advisor
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QSplitter
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal

from .hkmap import HKMapWidget
from .journey_form import JourneyForm
from .results_table import ResultsTable
from main import preference_to_optimization


# ── Background search worker ──────────────────────────────────────────────────

class JourneyWorker(QObject):
    """Runs the A* journey search on a background thread so the UI never freezes."""

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
        self.optimization = preference_to_optimization(preference)

    def run(self):
        try:
            from main import generate_journeys, rank_journeys, filter_journeys_by_transport
            journeys = generate_journeys(
                self.network, self.fare_lookup, self.origin, self.destination,
                optimization=self.optimization
            )
            if self.modes:
                journeys = filter_journeys_by_transport(journeys, set(self.modes))
            journeys = rank_journeys(journeys, self.preference)[:10]
            self.finished.emit(journeys)
        except Exception as e:
            self.error.emit(str(e))


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
        self._apply_theme()

    def _setup_ui(self):
        self.setWindowTitle("Smart Public Transport Advisor")
        self.setGeometry(80, 80, 1650, 960)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # ── Left panel: Journey Form ──────────────────────────────────────────
        self.form = JourneyForm(self.network.all_stops)
        self.form.populate_stops(self.network.all_stops)
        self.form.setFixedWidth(300)
        self.form.searchRequested.connect(self._on_search_requested)

        # ── Right side: map on top, results table below ───────────────────────
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
        stops = len(self.network.all_stops)
        segs  = self.network.get_num_segments()
        self.status_bar.showMessage(
            f"Network loaded  ·  {stops} stops  ·  {segs} segments  ·  "
            "Enter origin & destination then click Find Journeys"
        )

        self._searching_label = QLabel("  Searching…")
        self._searching_label.setStyleSheet(
            "color: #89b4fa; font-size: 12px; font-weight: 600; padding: 0 8px;"
        )
        self._searching_label.setVisible(False)
        self.status_bar.addPermanentWidget(self._searching_label)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_station_clicked(self, station_name: str):
        """Fill origin first, then destination, when user clicks a dot on the map."""
        origin = self.form.origin_combo.currentText().strip()
        dest   = self.form.dest_combo.currentText().strip()
        if not origin:
            self.form.origin_combo.setEditText(station_name)
            self.status_bar.showMessage(f"Origin set: {station_name}")
        elif not dest or dest == origin:
            self.form.dest_combo.setEditText(station_name)
            self.status_bar.showMessage(f"Destination set: {station_name}")
        else:
            # Both filled — restart the cycle
            self.form.origin_combo.setEditText(station_name)
            self.form.dest_combo.setEditText("")
            self.status_bar.showMessage(f"Origin reset: {station_name}  ·  Now pick a destination")

    def _on_search_requested(self, params: dict):
        origin      = params["origin"]
        destination = params["destination"]
        preference  = params["preference"]
        modes       = params["modes"]

        if not origin:
            self.status_bar.showMessage("Please enter an origin stop.")
            return
        if not destination:
            self.status_bar.showMessage("Please enter a destination stop.")
            return
        if origin not in self.network.all_stops:
            self.status_bar.showMessage(f"Origin '{origin}' not found in the network.")
            return
        if destination not in self.network.all_stops:
            self.status_bar.showMessage(f"Destination '{destination}' not found in the network.")
            return
        if origin == destination:
            self.status_bar.showMessage("Origin and destination must be different.")
            return

        # Prepare UI
        self.form.search_btn.setEnabled(False)
        self._searching_label.setVisible(True)
        self.results_table.clear()
        self.map_widget.clear_highlight()
        self.status_bar.showMessage(
            f"Searching {preference} route:  {origin}  →  {destination}…"
        )

        # Kick off background thread
        self._thread = QThread()
        self._worker = JourneyWorker(
            self.network, self.fare_lookup,
            origin, destination, preference, modes
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.error.connect(self._on_search_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_search_finished(self, journeys: list):
        self.form.search_btn.setEnabled(True)
        self._searching_label.setVisible(False)
        self.found_journeys = journeys

        if not journeys:
            self.status_bar.showMessage(
                "No journeys found — try relaxing the transport mode filters."
            )
            return

        self.results_table.set_journeys(journeys)
        self._on_journey_selected(0)  # auto-highlight the best journey
        self.status_bar.showMessage(
            f"Found {len(journeys)} journey(s)  ·  Click a row in the table to highlight it on the map"
        )

    def _on_search_error(self, msg: str):
        self.form.search_btn.setEnabled(True)
        self._searching_label.setVisible(False)
        self.status_bar.showMessage(f"Search error: {msg}")

    def _on_journey_selected(self, index: int):
        if 0 <= index < len(self.found_journeys):
            self.map_widget.highlight_journey(self.found_journeys[index])
            self.results_table.table.selectRow(index)
            self.results_table._show_details(index)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }

            /* ── Inputs ────────────────────────────────────────────────────── */
            QLineEdit, QComboBox {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 5px 10px;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #89b4fa; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }

            /* ── Table ─────────────────────────────────────────────────────── */
            QTableWidget {
                background-color: #181825;
                alternate-background-color: #1e1e2e;
                gridline-color: #313244;
                border: none;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: #cdd6f4;
            }
            QTableWidget::item:selected:active {
                background-color: #2a3050;
                color: #89b4fa;
            }
            QHeaderView::section {
                background-color: #181825;
                color: #6c7086;
                padding: 5px 8px;
                border: none;
                border-bottom: 1px solid #313244;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                text-transform: uppercase;
            }

            /* ── Splitter ──────────────────────────────────────────────────── */
            QSplitter::handle { background-color: #313244; }

            /* ── Scrollbars ────────────────────────────────────────────────── */
            QScrollBar:vertical   { background: #181825; width: 8px;  border: none; }
            QScrollBar:horizontal { background: #181825; height: 8px; border: none; }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #45475a; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #585b70;
            }
            QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }
            QScrollBar::add-page, QScrollBar::sub-page { background: none; }

            /* ── Status bar ────────────────────────────────────────────────── */
            QStatusBar {
                background-color: #181825;
                color: #6c7086;
                border-top: 1px solid #313244;
                font-size: 12px;
            }

            /* ── Tooltip ───────────────────────────────────────────────────── */
            QToolTip {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
            }
        """)



# ── Entry point ──────────────────────────────────────────────────────────────

def run_gui(network, fare_lookup):
    """Run the GUI application."""
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(network, fare_lookup)
    window.show()
    sys.exit(app.exec())
