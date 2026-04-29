"""
Network map visualization widget
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsTextItem, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter


# Color scheme for different transport modes
MODE_COLORS = {
    'MTR': QColor(0, 100, 200),           # Blue
    'Bus': QColor(0, 150, 50),            # Green
    'Light Rail': QColor(200, 100, 0),    # Orange/Brown
    'Walk': QColor(100, 100, 100),        # Gray
    'Airport Express': QColor(150, 0, 150), # Purple
}


class StationItem(QGraphicsEllipseItem):
    """Graphics item representing a station."""

    def __init__(self, name, x, y, mode='MTR', parent=None):
        # Create ellipse around the center point
        size = 20
        super().__init__(-size/2, -size/2, size, size, parent)
        self.setPos(x, y)
        self.station_name = name

        # Set color based on mode
        color = MODE_COLORS.get(mode, QColor(100, 100, 100))
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.White, 2))

        # Make it selectable
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)

        # Add label
        self.label = QGraphicsTextItem(name, self)
        self.label.setFont(QFont("Arial", 6))
        self.label.setDefaultTextColor(QColor(0, 0, 0))
        label_rect = self.label.boundingRect()
        self.label.setPos(-label_rect.width()/2, size/2 + 2)


class NetworkMap(QWidget):
    """Widget for displaying the transport network as a map."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = None
        self.journey_routes = []
        self.stop_positions = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Network Map")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Controls
        controls = QHBoxLayout()
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("Zoom Out")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(self.zoom_out_btn)

        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.clicked.connect(self._reset_view)
        controls.addWidget(self.reset_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Graphics view
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)

        # Status label
        self.status_label = QLabel("No network loaded")
        layout.addWidget(self.status_label)

        self.scale_factor = 1.0

    def set_network(self, network):
        """Set the transport network to display."""
        self.network = network
        self._render_network()

    def _render_network(self):
        """Render the network on the scene."""
        self.scene.clear()
        self.stop_positions = {}

        if not self.network:
            return

        # Get all stops and segments
        all_stops = sorted(self.network.all_stops)
        segments_by_stop = self.network.stops

        if not all_stops:
            self.status_label.setText("No stops to display")
            return

        # Calculate layout positions using force-directed algorithm
        self._calculate_layout(all_stops, segments_by_stop)

        # Draw edges first (so they appear behind nodes)
        for stop, outgoing in segments_by_stop.items():
            if stop not in self.stop_positions:
                continue
            from_pos = self.stop_positions[stop]

            for segment in outgoing:
                to_stop = segment.to_stop
                if to_stop not in self.stop_positions:
                    continue
                to_pos = self.stop_positions[to_stop]

                # Get color for this transport mode
                color = MODE_COLORS.get(segment.mode_of_transport, QColor(150, 150, 150))

                # Create line
                line = QGraphicsLineItem(from_pos.x(), from_pos.y(),
                                        to_pos.x(), to_pos.y())
                line.setPen(QPen(color, 2))
                line.setZValue(0)  # Behind stations
                self.scene.addItem(line)

        # Draw stations
        for stop in all_stops:
            if stop not in self.stop_positions:
                continue

            pos = self.stop_positions[stop]
            # Determine mode (use first segment's mode as representative)
            mode = 'MTR'  # Default
            if stop in segments_by_stop and segments_by_stop[stop]:
                mode = segments_by_stop[stop][0].mode_of_transport

            station = StationItem(stop, pos.x(), pos.y(), mode)
            station.setZValue(1)  # Above lines
            self.scene.addItem(station)

        # Fit view to content
        self._fit_view()
        self.status_label.setText(f"Network: {len(all_stops)} stops")

    def _calculate_layout(self, stops, segments_by_stop):
        """Calculate positions for stations using a simple force-directed layout."""
        import random

        # Initialize with random positions
        random.seed(42)  # For reproducibility
        width, height = 800, 600

        for stop in stops:
            x = random.uniform(50, width - 50)
            y = random.uniform(50, height - 50)
            self.stop_positions[stop] = QPointF(x, y)

        # Simple force-directed iterations
        for _ in range(50):
            # Repulsion between all nodes
            for stop1 in stops:
                if stop1 not in self.stop_positions:
                    continue
                pos1 = self.stop_positions[stop1]
                dx, dy = 0, 0

                for stop2 in stops:
                    if stop1 == stop2 or stop2 not in self.stop_positions:
                        continue
                    pos2 = self.stop_positions[stop2]

                    dist = max(1, ((pos1.x() - pos2.x())**2 + (pos1.y() - pos2.y())**2)**0.5)
                    repulsion = 5000 / (dist * dist)
                    dx += (pos1.x() - pos2.x()) / dist * repulsion
                    dy += (pos1.y() - pos2.y()) / dist * repulsion

                # Attraction along edges
                for segment in segments_by_stop.get(stop1, []):
                    to_stop = segment.to_stop
                    if to_stop not in self.stop_positions:
                        continue
                    pos2 = self.stop_positions[to_stop]

                    dist = max(1, ((pos1.x() - pos2.x())**2 + (pos1.y() - pos2.y())**2)**0.5)
                    attraction = dist * 0.01
                    dx += (pos2.x() - pos1.x()) * attraction
                    dy += (pos2.y() - pos1.y()) * attraction

                # Apply movement
                new_x = pos1.x() + dx * 0.1
                new_y = pos1.y() + dy * 0.1
                # Clamp to bounds
                new_x = max(50, min(width - 50, new_x))
                new_y = max(50, min(height - 50, new_y))
                self.stop_positions[stop1] = QPointF(new_x, new_y)

    def _fit_view(self):
        """Fit the view to show all items."""
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        # Add padding
        rect.adjust(-30, -30, 30, 30)
        self.view.fitInView(rect)

    def _zoom_in(self):
        """Zoom in."""
        self.view.scale(1.2, 1.2)

    def _zoom_out(self):
        """Zoom out."""
        self.view.scale(0.8, 0.8)

    def _reset_view(self):
        """Reset view to fit all content."""
        self._fit_view()

    def highlight_journey(self, journey):
        """Highlight a journey route on the map."""
        if not journey or not self.stop_positions:
            return

        # Get segment coordinates
        for segment in journey.segments:
            from_stop = segment.from_stop
            to_stop = segment.to_stop

            if from_stop not in self.stop_positions or to_stop not in self.stop_positions:
                continue

            from_pos = self.stop_positions[from_stop]
            to_pos = self.stop_positions[to_stop]

            # Draw highlighted line
            line = QGraphicsLineItem(from_pos.x(), from_pos.y(),
                                    to_pos.x(), to_pos.y())
            line.setPen(QPen(QColor(255, 0, 0), 4))  # Red, thick
            line.setZValue(2)  # Above everything
            self.scene.addItem(line)

        self.status_label.setText(f"Journey: {journey.origin} → {journey.destination}")

    def clear_highlight(self):
        """Clear any highlighted journey."""
        self._render_network()