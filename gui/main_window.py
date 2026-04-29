"""
Main GUI window for Smart Public Transport Advisor
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QMessageBox, QStatusBar,
    QSplitter
)
from PyQt6.QtCore import Qt

from .hkmap import HKMapWidget


class MainWindow(QMainWindow):
    """Main application window for the GUI."""

    def __init__(self, network, fare_lookup):
        super().__init__()
        self.network = network
        self.fare_lookup = fare_lookup
        self.found_journeys = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Smart Public Transport Advisor - GUI")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout - horizontal splitter
        main_layout = QHBoxLayout(central)

        # Left panel - input form
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Title
        title = QLabel("Find a Journey")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_layout.addWidget(title)

        # Origin
        left_layout.addWidget(QLabel("From:"))
        self.origin_input = QLineEdit()
        left_layout.addWidget(self.origin_input)

        # Destination
        left_layout.addWidget(QLabel("To:"))
        self.dest_input = QLineEdit()
        left_layout.addWidget(self.dest_input)

        # Search button
        self.search_btn = QPushButton("Find Journeys")
        self.search_btn.clicked.connect(self._on_search_clicked)
        left_layout.addWidget(self.search_btn)

        # Results label
        self.results_label = QLabel("")
        left_layout.addWidget(self.results_label)

        left_layout.addStretch()

        # Right panel - map
        self.map_widget = HKMapWidget()
        self.map_widget.set_network(self.network)

        # Splitter
        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.map_widget)
        splitter.setSizes([350, 1050])

        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _on_search_clicked(self):
        """Handle search button click."""
        origin = self.origin_input.text().strip()
        destination = self.dest_input.text().strip()

        if not origin or not destination:
            self.results_label.setText("Please enter both origin and destination")
            return

        if origin not in self.network.all_stops:
            self.results_label.setText(f"Origin '{origin}' not found")
            return

        if destination not in self.network.all_stops:
            self.results_label.setText(f"Destination '{destination}' not found")
            return

        # Import from main
        from main import generate_journeys, rank_journeys

        journeys = generate_journeys(self.network, self.fare_lookup, origin, destination)
        journeys = rank_journeys(journeys, "fastest")

        self.found_journeys = journeys

        if journeys:
            j = journeys[0]
            self.results_label.setText(
                f"Found {len(journeys)} journeys. Best: {j.num_segments} segments, "
                f"{j.total_duration} min, ${j.total_cost:.2f}"
            )
            # Highlight on map
            self.map_widget.highlight_journey(j)
        else:
            self.results_label.setText("No journeys found")


def run_gui(network, fare_lookup):
    """Run the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow(network, fare_lookup)
    window.show()

    sys.exit(app.exec())