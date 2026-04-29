"""
Hong Kong Map Visualization Widget
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap


# Color scheme for different transport modes
MODE_COLORS = {
    'MTR': QColor(0, 100, 200),           # Blue
    'Bus': QColor(0, 150, 50),            # Green
    'Light Rail': QColor(200, 100, 0),  # Orange
    'Walk': QColor(100, 100, 100),        # Gray
    'Airport Express': QColor(150, 0, 150),  # Purple
}


# Accurate station coordinates from verified data
STATION_COORDS = {
    'Admiralty': (22.2788, 114.1646),
    'Airport': (22.316, 113.9366),
    'AsiaWorld-Expo': (22.3218, 113.9412),
    'Austin': (22.3046, 114.1665),
    'Causeway Bay': (22.2802, 114.1835),
    'Central': (22.282, 114.1576),
    'Chai Wan': (22.2644, 114.2368),
    'Che Kung Temple': (22.3748, 114.1861),
    'Cheung Sha Wan': (22.3354, 114.1563),
    'Choi Hung': (22.3348, 114.2089),
    'City One': (22.3828, 114.2035),
    'Diamond Hill': (22.3401, 114.2016),
    'Disneyland Resort': (22.3155, 114.0451),
    'East Tsim Sha Tsui': (22.2955, 114.1754),
    'Fanling': (22.4921, 114.1387),
    'Fo Tan': (22.3953, 114.1982),
    'Fortress Hill': (22.2881, 114.1936),
    'HKU': (22.2841, 114.1356),
    'Hang Hau': (22.3156, 114.2644),
    'Heng Fa Chuen': (22.2769, 114.2398),
    'Heng On': (22.4174, 114.2258),
    'Hin Keng': (22.364, 114.1708),
    'Ho Man Tin': (22.3093, 114.1829),
    'Hong Kong': (22.285, 114.158),
    'Hung Hom': (22.3029, 114.1816),
    'Jordan': (22.3049, 114.1718),
    'Kai Tak': (22.3304, 114.1994),
    'Kam Sheung Road': (22.4348, 114.0634),
    'Kennedy Town': (22.2812, 114.1285),
    'Kowloon Bay': (22.3235, 114.2141),
    'Kowloon Tong': (22.337, 114.1762),
    'Kowloon': (22.3049, 114.1615),
    'Kwai Fong': (22.3569, 114.1279),
    'Kwai Hing': (22.3632, 114.1312),
    'Kwun Tong': (22.3121, 114.2265),
    'LOHAS Park': (22.2957, 114.2689),
    'Lai Chi Kok': (22.3373, 114.1482),
    'Lai King': (22.3484, 114.1261),
    'Lam Tin': (22.3068, 114.233),
    'Lei Tung': (22.2421, 114.1562),
    'Lo Wu': (22.5283, 114.1134),
    'Lok Fu': (22.338, 114.1871),
    'Lok Ma Chau': (22.5144, 114.0657),
    'Long Ping': (22.4477, 114.0253),
    'Ma On Shan': (22.4247, 114.2316),
    'Mei Foo': (22.3381, 114.1376),
    'Mong Kok East': (22.3222, 114.1728),
    'Mong Kok': (22.3191, 114.1694),
    'Nam Cheong': (22.3268, 114.1533),
    'Ngau Tau Kok': (22.3154, 114.2193),
    'North Point': (22.2909, 114.2007),
    'Ocean Park': (22.2486, 114.1743),
    'Olympic': (22.3178, 114.1602),
    'Po Lam': (22.3224, 114.258),
    'Prince Edward': (22.3245, 114.1683),
    'Quarry Bay': (22.2878, 114.2096),
    'Sai Wan Ho': (22.2816, 114.2224),
    'Sai Ying Pun': (22.2856, 114.1427),
    'Sha Tin Wai': (22.3771, 114.195),
    'Sha Tin': (22.3825, 114.1875),
    'Sham Shui Po': (22.3307, 114.1623),
    'Shau Kei Wan': (22.2789, 114.2289),
    'Shek Kip Mei': (22.332, 114.1687),
    'Shek Mun': (22.3877, 114.2083),
    'Sheung Shui': (22.5012, 114.128),
    'Sheung Wan': (22.2862, 114.1518),
    'Siu Hong': (22.412, 113.9786),
    'South Horizons': (22.2425, 114.1491),
    'Sunny Bay': (22.3318, 114.0288),
    'Tai Koo': (22.2846, 114.2161),
    'Tai Po Market': (22.4446, 114.1706),
    'Tai Shui Hang': (22.4088, 114.223),
    'Tai Wai': (22.3731, 114.1786),
    'Tai Wo Hau': (22.3708, 114.125),
    'Tai Wo': (22.4511, 114.1611),
    'Tin Hau': (22.2827, 114.1917),
    'Tin Shui Wai': (22.4481, 114.0046),
    'Tiu Keng Leng': (22.3042, 114.2524),
    'Tseung Kwan O': (22.3074, 114.26),
    'Tsim Sha Tsui': (22.2973, 114.1722),
    'Tsing Yi': (22.3584, 114.107),
    'Tsuen Wan West': (22.3686, 114.1098),
    'Tsuen Wan': (22.3736, 114.1178),
    'Tuen Mun': (22.3952, 113.9731),
    'Tung Chung': (22.2893, 113.9416),
    'University': (22.4134, 114.2102),
    'Wan Chai': (22.2773, 114.1728),
    'Whampo': (22.305, 114.1896),
    'Wong Chuk Hang': (22.248, 114.1681),
    'Wong Tai Sin': (22.3417, 114.1939),
    'Wu Kai Sha': (22.4291, 114.2438),
    'Yau Ma Tei': (22.3129, 114.1707),
    'Yau Tong': (22.2979, 114.2371),
    'Yuen Long': (22.4461, 114.0352),
}

# Map image dimensions (from Hong Kong Base Map.png)
MAP_PIXEL_WIDTH = 3214
MAP_PIXEL_HEIGHT = 2339

# Geographic bounds of the map image
MAP_WEST = 113.83   # Min longitude (left edge)
MAP_EAST = 114.44   # Max longitude (right edge)
MAP_NORTH = 22.56  # Max latitude (top edge)
MAP_SOUTH = 22.15  # Min latitude (bottom edge)


def map_range(lat, lon):
    """Map latitude/longitude to pixel coordinates on the map image.

    Args:
        lat: Latitude (22.15 to 22.56)
        lon: Longitude (113.83 to 114.44)

    Returns:
        Tuple of (x, y) pixel coordinates

    X-axis: West (113.83) -> 0 (left), East (114.44) -> MAP_PIXEL_WIDTH (right)
    Y-axis: North (22.56) -> 0 (top), South (22.15) -> MAP_PIXEL_HEIGHT (bottom)

    Offset applied: +150 X (east), +200 Y (south) for visual alignment.
    """
    x = (lon - MAP_WEST) / (MAP_EAST - MAP_WEST) * MAP_PIXEL_WIDTH + 85
    y = (MAP_NORTH - lat) / (MAP_NORTH - MAP_SOUTH) * MAP_PIXEL_HEIGHT + 85
    return x, y


class HKMapWidget(QWidget):
    """Widget for displaying Hong Kong transport map."""

    stationClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = None
        self.stop_positions = {}
        self.highlighted_path = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Hong Kong Transport Map")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Fit the view to the map image initially
        self.view.fitInView(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT)
        layout.addWidget(self.view)

        self._load_background()

        controls = QHBoxLayout()
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setMaximumWidth(30)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setMaximumWidth(30)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(self.zoom_out_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._reset_view)
        controls.addWidget(self.reset_btn)

        controls.addStretch()
        layout.addLayout(controls)

        self.status_label = QLabel("No journey selected")
        layout.addWidget(self.status_label)

    def _load_background(self):
        try:
            if os.path.exists('Hong_Kong_Base_Map.png'):
                pixmap = QPixmap('Hong_Kong_Base_Map.png')
                self.bg_item = self.scene.addPixmap(pixmap)
                self.bg_item.setZValue(-1)
        except Exception as e:
            print(f"Error loading background: {e}")

    def set_network(self, network):
        self.network = network
        self._render_stations()

    def _render_stations(self):
        if not self.network:
            return

        for stop in self.network.all_stops:
            if stop in STATION_COORDS:
                lat, lon = STATION_COORDS[stop]
                x, y = map_range(lat, lon)
                self.stop_positions[stop] = (x, y)

                # Determine color
                color = MODE_COLORS.get('MTR', QColor(100, 100, 100))

                # Scale station marker to map size (larger for high-res map)
                size = 16
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(color))
                ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
                ellipse.setZValue(1)
                self.scene.addItem(ellipse)

        self.status_label.setText(f"Showing {len(self.stop_positions)} stations")

    def highlight_journey(self, journey):
        if not journey:
            return

        self._render_stations()
        self.highlighted_path = journey.segments

        prev_pos = None
        for seg in journey.segments:
            from_pos = self.stop_positions.get(seg.from_stop)
            to_pos = self.stop_positions.get(seg.to_stop)

            if from_pos and to_pos:
                line = QGraphicsLineItem(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                line.setPen(QPen(QColor(255, 0, 0), 3))
                line.setZValue(2)
                self.scene.addItem(line)
                prev_pos = to_pos
            elif from_pos:
                ellipse = QGraphicsEllipseItem(from_pos[0] - 6, from_pos[1] - 6, 12, 12)
                ellipse.setBrush(QBrush(QColor(0, 200, 0)))
                ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
                ellipse.setZValue(2)
                self.scene.addItem(ellipse)
                prev_pos = from_pos

        if prev_pos:
            ellipse = QGraphicsEllipseItem(prev_pos[0] - 6, prev_pos[1] - 6, 12, 12)
            ellipse.setBrush(QBrush(QColor(255, 0, 0)))
            ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
            ellipse.setZValue(2)
            self.scene.addItem(ellipse)

        self.status_label.setText(f"Journey: {journey.origin} → {journey.destination} ({journey.num_segments} segments)")

    def _zoom_in(self):
        self.view.scale(1.2, 1.2)

    def _zoom_out(self):
        self.view.scale(0.8, 0.8)

    def _reset_view(self):
        self.view.resetTransform()
        self._render_stations()