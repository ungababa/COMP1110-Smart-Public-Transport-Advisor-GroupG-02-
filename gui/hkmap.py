"""
Hong Kong Map Visualization Widget
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
    QPushButton, QHBoxLayout, QGraphicsTextItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QFont


# ── Transport mode colours ────────────────────────────────────────────────────
MODE_COLORS = {
    'MTR':            QColor(0, 100, 200),
    'Bus':            QColor(0, 150, 50),
    'Light Rail':     QColor(200, 100, 0),
    'Walk':           QColor(100, 100, 100),
    'Airport Express':QColor(150, 0, 150),
}

# ── MTR station coordinates (WGS84) ──────────────────────────────────────────
# Corrected coordinates verified against official MTR map
STATION_COORDS = {
    'Admiralty':          (22.2794, 114.1651),
    'Airport':            (22.3160, 113.9366),
    'AsiaWorld-Expo':     (22.3218, 113.9412),
    'Austin':             (22.3046, 114.1670),
    'Causeway Bay':       (22.2802, 114.1835),
    'Central':            (22.2820, 114.1576),
    'Chai Wan':           (22.2644, 114.2368),
    'Che Kung Temple':    (22.3748, 114.1861),
    'Cheung Sha Wan':     (22.3354, 114.1563),
    'Choi Hung':          (22.3348, 114.2089),
    'City One':           (22.3828, 114.2035),
    'Diamond Hill':       (22.3401, 114.2016),
    'Disneyland Resort':  (22.3155, 114.0451),
    'East Tsim Sha Tsui': (22.2955, 114.1754),
    'Fanling':            (22.4921, 114.1387),
    'Fo Tan':             (22.3953, 114.1982),
    'Fortress Hill':      (22.2881, 114.1936),
    'HKU':                (22.2841, 114.1354),
    'Hang Hau':           (22.3156, 114.2644),
    'Heng Fa Chuen':      (22.2769, 114.2398),
    'Heng On':            (22.4174, 114.2258),
    'Hin Keng':           (22.3640, 114.1708),
    'Ho Man Tin':         (22.3093, 114.1829),
    'Hong Kong':          (22.2850, 114.1580),
    'Hung Hom':           (22.3029, 114.1816),
    'Jordan':             (22.3049, 114.1718),
    'Kai Tak':            (22.3304, 114.1994),
    'Kam Sheung Road':    (22.4348, 114.0634),
    'Kennedy Town':       (22.2815, 114.1283),
    'Kowloon Bay':        (22.3235, 114.2141),
    'Kowloon Tong':       (22.3370, 114.1762),
    'Kowloon':            (22.3049, 114.1615),
    'Kwai Fong':          (22.3569, 114.1279),
    'Kwai Hing':          (22.3632, 114.1312),
    'Kwun Tong':          (22.3121, 114.2265),
    'LOHAS Park':         (22.2957, 114.2689),
    'Lai Chi Kok':        (22.3373, 114.1482),
    'Lai King':           (22.3484, 114.1261),
    'Lam Tin':            (22.3068, 114.2330),
    'Lei Tung':           (22.2421, 114.1562),
    'Lo Wu':              (22.5283, 114.1134),
    'Lok Fu':             (22.3380, 114.1871),
    'Lok Ma Chau':        (22.5144, 114.0657),
    'Long Ping':          (22.4477, 114.0253),
    'Ma On Shan':         (22.4247, 114.2316),
    'Mei Foo':            (22.3381, 114.1376),
    'Mong Kok East':      (22.3222, 114.1728),
    'Mong Kok':           (22.3191, 114.1694),
    'Nam Cheong':         (22.3268, 114.1533),
    'Ngau Tau Kok':       (22.3154, 114.2193),
    'North Point':        (22.2909, 114.2007),
    'Ocean Park':         (22.2486, 114.1743),
    'Olympic':            (22.3178, 114.1602),
    'Po Lam':             (22.3224, 114.2580),
    'Prince Edward':      (22.3245, 114.1683),
    'Quarry Bay':         (22.2878, 114.2096),
    'Sai Wan Ho':         (22.2816, 114.2224),
    'Sai Ying Pun':       (22.2856, 114.1430),
    'Sha Tin Wai':        (22.3771, 114.1950),
    'Sha Tin':            (22.3825, 114.1875),
    'Sham Shui Po':       (22.3307, 114.1623),
    'Shau Kei Wan':       (22.2789, 114.2289),
    'Shek Kip Mei':       (22.3320, 114.1687),
    'Shek Mun':           (22.3877, 114.2083),
    'Sheung Shui':        (22.5012, 114.1280),
    'Sheung Wan':         (22.2862, 114.1518),
    'Siu Hong':           (22.4120, 113.9786),
    'South Horizons':     (22.2425, 114.1491),
    'Sunny Bay':          (22.3318, 114.0288),
    'Tai Koo':            (22.2846, 114.2161),
    'Tai Po Market':      (22.4446, 114.1706),
    'Tai Shui Hang':      (22.4088, 114.2230),
    'Tai Wai':            (22.3731, 114.1786),
    'Tai Wo Hau':         (22.3708, 114.1250),
    'Tai Wo':             (22.4511, 114.1611),
    'Tin Hau':            (22.2827, 114.1917),
    'Tin Shui Wai':       (22.4481, 114.0046),
    'Tiu Keng Leng':      (22.3042, 114.2524),
    'Tseung Kwan O':      (22.3074, 114.2600),
    'Tsim Sha Tsui':      (22.2973, 114.1722),
    'Tsing Yi':           (22.3584, 114.1070),
    'Tsuen Wan West':     (22.3686, 114.1098),
    'Tsuen Wan':          (22.3736, 114.1178),
    'Tuen Mun':           (22.3952, 113.9731),
    'Tung Chung':         (22.2893, 113.9416),
    'University':         (22.4134, 114.2102),
    'Wan Chai':           (22.2773, 114.1728),
    'Whampo':             (22.3050, 114.1896),
    'Wong Chuk Hang':     (22.2480, 114.1681),
    'Wong Tai Sin':       (22.3417, 114.1939),
    'Wu Kai Sha':         (22.4291, 114.2438),
    'Yau Ma Tei':         (22.3129, 114.1707),
    'Yau Tong':           (22.2979, 114.2371),
    'Yuen Long':          (22.4461, 114.0352),
}

# ── Map geometry ──────────────────────────────────────────────────────────────
MAP_PIXEL_WIDTH  = 3214
MAP_PIXEL_HEIGHT = 2339

MAP_WEST  = 113.83
MAP_EAST  = 114.44
MAP_NORTH = 22.56
MAP_SOUTH = 22.15


def map_range(lat, lon):
    """Convert lat/lon to pixel coordinates on the map image."""
    x = (lon - MAP_WEST)  / (MAP_EAST  - MAP_WEST)  * MAP_PIXEL_WIDTH  + 90
    y = (MAP_NORTH - lat) / (MAP_NORTH - MAP_SOUTH) * MAP_PIXEL_HEIGHT + 80
    return x, y


# ── Bus stop loaders (unchanged from teammate's implementation) ────────────────

def load_bus_stops():
    """Load bus stop coordinates from STOP_BUS.xml and RSTOP_BUS.xml."""
    stop_id_coords   = {}
    stop_name_coords = {}
    stop_id_to_names = {}  # stop_id -> set of stop_names
    
    # Load coordinates from STOP_BUS.xml by stop_id
    xml_paths = [
        Path('data/bus/STOP_BUS.xml'),
        Path('gui/../data/bus/STOP_BUS.xml'),
        Path(__file__).parent.parent / 'data' / 'bus' / 'STOP_BUS.xml',
    ]
    
    xml_file = None
    for path in xml_paths:
        if path.exists():
            xml_file = path
            break
    
    if xml_file:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for stop_elem in root.findall('STOP'):
                stop_id = stop_elem.findtext('STOP_ID')
                lat_str = stop_elem.findtext('X')
                lon_str = stop_elem.findtext('Y')
                
                if stop_id and lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                        stop_id_coords[stop_id] = (lat, lon)
                    except ValueError:
                        continue
            
            print(f"Loaded {len(stop_id_coords)} bus stops from STOP_BUS.xml")
        
        except Exception as e:
            print(f"Error loading bus stops: {e}")
    else:
        print("Warning: STOP_BUS.xml not found.")
    
    # Load stop names from RSTOP_BUS.xml and map to coordinates
    xml_paths = [
        Path('data/bus/RSTOP_BUS.xml'),
        Path('gui/../data/bus/RSTOP_BUS.xml'),
        Path(__file__).parent.parent / 'data' / 'bus' / 'RSTOP_BUS.xml',
    ]
    
    xml_file = None
    for path in xml_paths:
        if path.exists():
            xml_file = path
            break
    
    if xml_file:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for route_elem in root.findall('RSTOP'):
                stop_id = route_elem.findtext('STOP_ID')
                # Get English name (STOP_NAMEE)
                stop_name = route_elem.findtext('STOP_NAMEE')
                
                if stop_id and stop_name and stop_id in stop_id_coords:
                    if stop_id not in stop_id_to_names:
                        stop_id_to_names[stop_id] = set()
                    stop_id_to_names[stop_id].add(stop_name)
                    # Map stop name to coordinates (only add if not already mapped)
                    if stop_name not in stop_name_coords:
                        stop_name_coords[stop_name] = stop_id_coords[stop_id]
        
        except Exception as e:
            print(f"Error loading stop names: {e}")
    else:
        print("Warning: RSTOP_BUS.xml not found.")

    print(f"Loaded {len(stop_name_coords)} named bus stops for journey mapping")
    return stop_id_coords, stop_name_coords


def identify_important_bus_stations(stop_id_coords):
    """Return the top 300 bus stops by route density."""
    stop_route_count = {}
    important_stops  = {}
    
    # Try to find the XML file in bus directory
    xml_paths = [
        Path('data/bus/RSTOP_BUS.xml'),
        Path('gui/../data/bus/RSTOP_BUS.xml'),
        Path(__file__).parent.parent / 'data' / 'bus' / 'RSTOP_BUS.xml',
    ]
    
    xml_file = None
    for path in xml_paths:
        if path.exists():
            xml_file = path
            break
    
    if not xml_file:
        print("Warning: RSTOP_BUS.xml not found. All bus stops will be treated equally.")
        return important_stops
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Count routes per stop
        for route_elem in root.findall('RSTOP'):
            stop_id = route_elem.findtext('STOP_ID')
            if stop_id and stop_id in stop_id_coords:
                stop_route_count[stop_id] = stop_route_count.get(stop_id, 0) + 1
        
        # Select top 300 stops by route count
        MAX_IMPORTANT_STOPS = 300
        sorted_stops = sorted(stop_route_count.items(), key=lambda x: x[1], reverse=True)
        for stop_id, count in sorted_stops[:MAX_IMPORTANT_STOPS]:
            important_stops[stop_id] = count
    
    except Exception as e:
        print(f"Error identifying important bus stations: {e}")
    
    print(f"Identified {len(important_stops)} top important bus interchanges (top 300 by route density)")
    return important_stops


# ── Custom QGraphicsView with scroll-zoom and click detection ─────────────────

class _MapView(QGraphicsView):
    """QGraphicsView subclass that adds scroll-wheel zoom and clickable station dots."""

    stationClicked = pyqtSignal(str)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Maps graphics item → station name for click detection
        self._station_map: dict = {}
        self._press_pos = None

    def register_station(self, name: str, item: QGraphicsEllipseItem):
        self._station_map[item] = name

    def clear_station_registry(self):
        self._station_map.clear()

    def wheelEvent(self, event):
        """Scroll-wheel zooms in/out centred on the cursor."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Treat release as a click only when the mouse barely moved (not a drag)."""
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            delta = event.pos() - self._press_pos
            if delta.manhattanLength() < 6:
                scene_pos = self.mapToScene(event.pos())
                hit = self.scene().items(
                    QRectF(scene_pos.x() - 12, scene_pos.y() - 12, 24, 24)
                )
                for item in hit:
                    if item in self._station_map:
                        self.stationClicked.emit(self._station_map[item])
                        self._press_pos = None
                        super().mouseReleaseEvent(event)
                        return
        self._press_pos = None
        super().mouseReleaseEvent(event)


# ── Main map widget ───────────────────────────────────────────────────────────

class HKMapWidget(QWidget):
    """Widget for displaying Hong Kong transport map."""

    stationClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = None
        self.stop_positions      = {}   # MTR station name → (x, y) pixels
        self._station_items      = {}   # MTR station name → ellipse item
        self._path_items         = []   # items drawn for the current journey (cleared on next search)

        # Bus stop data
        self.bus_stops_by_id, self.bus_stops_by_name = load_bus_stops()
        self.important_bus_stops = identify_important_bus_stations(self.bus_stops_by_id)
        self.bus_stop_positions      = {}   # stop_id   → (x, y)
        self.bus_stop_name_positions = {}   # stop_name → (x, y)

        # Pre-compute pixel coords for bus stops
        for stop_id, (lat, lon) in self.bus_stops_by_id.items():
            self.bus_stop_positions[stop_id] = map_range(lat, lon)
        for stop_name, (lat, lon) in self.bus_stops_by_name.items():
            self.bus_stop_name_positions[stop_name] = map_range(lat, lon)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Hong Kong Transport Map")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 2px 4px;")
        header.addWidget(title)
        header.addStretch()

        for label, tip, slot in [
            ("+", "Zoom in  (or scroll ↑)",  self._zoom_in),
            ("−", "Zoom out (or scroll ↓)",  self._zoom_out),
            ("⊡", "Reset view",              self._reset_view),
        ]:
            btn = QPushButton(label)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            header.addWidget(btn)

        layout.addLayout(header)

        # Scene + custom view
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT)

        self.view = _MapView(self.scene)
        self.view.stationClicked.connect(self.stationClicked)
        layout.addWidget(self.view)

        # Controls row (kept compact)
        controls = QHBoxLayout()
        controls.addStretch()
        layout.addLayout(controls)

        self.status_label = QLabel("No journey selected")
        self.status_label.setStyleSheet("padding: 2px 4px; font-size: 11px;")
        layout.addWidget(self.status_label)

        self._load_background()

    def _load_background(self):
        # Prefer the dark stylised map; fall back to the standard base map
        root = Path(__file__).parent.parent
        candidates = [
            Path('Hong_Kong_Dark_Map.png'),
            root / 'Hong_Kong_Dark_Map.png',
            Path('Hong_Kong_Base_Map.png'),
            root / 'Hong_Kong_Base_Map.png',
            Path('data/Hong_Kong_Base_Map.png'),
            root / 'data' / 'Hong_Kong_Base_Map.png',
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    pixmap = QPixmap(str(candidate))
                    bg = self.scene.addPixmap(pixmap)
                    bg.setZValue(-1)
                    print(f"Map background loaded: {candidate}")
                    return
                except Exception as e:
                    print(f"Error loading {candidate}: {e}")
        print("Warning: no map background file found.")

    def set_network(self, network):
        self.network = network
        self._render_stations()

    def _render_stations(self):
        """Draw all MTR stations + top bus stops. Called once at startup."""
        if not self.network:
            return

        # Clear old station items first
        for item in self._station_items.values():
            self.scene.removeItem(item)
        self._station_items.clear()
        self.stop_positions.clear()
        self.view.clear_station_registry()

        mtr_count = 0
        important_bus_count = 0

        # MTR stations
        for stop in self.network.all_stops:
            if stop in STATION_COORDS:
                lat, lon = STATION_COORDS[stop]
                x, y = map_range(lat, lon)
                self.stop_positions[stop] = (x, y)

                size = 16
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(MODE_COLORS['MTR']))
                ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
                ellipse.setZValue(1)
                ellipse.setToolTip(stop)
                self.scene.addItem(ellipse)
                self._station_items[stop] = ellipse
                self.view.register_station(stop, ellipse)
                mtr_count += 1

        # Important bus stops
        for stop_id in self.important_bus_stops:
            if stop_id in self.bus_stop_positions:
                x, y = self.bus_stop_positions[stop_id]
                size = 8
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(QColor(0, 150, 50)))
                ellipse.setPen(QPen(Qt.GlobalColor.white, 1))
                ellipse.setZValue(1)
                self.scene.addItem(ellipse)
                important_bus_count += 1

        self.view.fitInView(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT,
                            Qt.AspectRatioMode.KeepAspectRatio)
        self.status_label.setText(
            f"Showing {mtr_count} MTR stations + {important_bus_count} important bus interchanges  ·  "
            "Scroll to zoom  ·  Drag to pan  ·  Click a station to select it"
        )

    # ── Journey highlighting ──────────────────────────────────────────────────

    def highlight_journey(self, journey):
        """Draw the journey on the map. Clears only the previous journey's items."""
        self.clear_highlight()
        if not journey:
            return

        font = QFont()
        font.setPointSize(8)

        all_journey_positions = {}   # stop_name → (x, y) for all resolved stops

        journey_bus_stops_found = set()
        all_journey_stops = {}  # stop_name -> position for labeling
        
        for seg in journey.segments:
            from_pos = self.stop_positions.get(seg.from_stop)
            to_pos   = self.stop_positions.get(seg.to_stop)

            # Fall back to bus stop positions if not an MTR station
            if from_pos is None and seg.from_stop in self.bus_stop_name_positions:
                from_pos = self.bus_stop_name_positions[seg.from_stop]
            if to_pos is None and seg.to_stop in self.bus_stop_name_positions:
                to_pos = self.bus_stop_name_positions[seg.to_stop]

            if from_pos:
                all_journey_positions[seg.from_stop] = from_pos
            if to_pos:
                all_journey_positions[seg.to_stop] = to_pos

            # Draw line between the two stops
            if from_pos and to_pos:
                color = MODE_COLORS.get(seg.mode_of_transport, QColor(200, 50, 50))
                # White shadow line underneath for contrast on dark map
                shadow = QGraphicsLineItem(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                shadow.setPen(QPen(QColor(255, 255, 255, 60), 7))
                shadow.setZValue(1)
                self.scene.addItem(shadow)
                self._path_items.append(shadow)
                # Coloured line on top
                # Both are MTR stations
                line = QGraphicsLineItem(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                line.setPen(QPen(color, 4))
                line.setZValue(2)
                self.scene.addItem(line)
                self._path_items.append(line)

        # Draw dots + labels for every stop in the journey
        for stop_name, (x, y) in all_journey_positions.items():
            is_mtr = stop_name in STATION_COORDS

            # Highlight dot — white fill with a coloured ring
            size = 16 if is_mtr else 11
            ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
            ellipse.setBrush(QBrush(QColor(255, 255, 255)))          # white fill
            ring_color = QColor(255, 210, 50) if is_mtr else QColor(255, 140, 0)
            ellipse.setPen(QPen(ring_color, 3))
            ellipse.setZValue(3)
            self.scene.addItem(ellipse)
            self._path_items.append(ellipse)

            # Label — dark text on a semi-transparent light pill for readability
            text = QGraphicsTextItem(stop_name)
            text.setFont(font)
            text.setDefaultTextColor(QColor(15, 20, 40))             # very dark navy
            # Offset slightly from the dot
            text.setPos(x + size // 2 + 4, y - 9)
            text.setZValue(4)
            # Background rect behind text
            br = text.boundingRect()
            bg_rect = self.scene.addRect(
                x + size // 2 + 3, y - 10,
                br.width() + 4, br.height() + 2,
                QPen(Qt.PenStyle.NoPen),
                QBrush(QColor(255, 255, 255, 190)),  # semi-transparent white pill
            )
            bg_rect.setZValue(3)
            self.scene.addItem(text)
            self._path_items.append(bg_rect)
            self._path_items.append(text)

        # Origin marker (green)
        origin_pos = all_journey_positions.get(journey.origin)
        if origin_pos:
            m = self._add_endpoint_marker(origin_pos, QColor(0, 220, 100), 20)
            self._path_items.append(m)

        # Destination marker (red)
        dest_pos = all_journey_positions.get(journey.destination)
        if dest_pos:
            m = self._add_endpoint_marker(dest_pos, QColor(220, 50, 50), 20)
            self._path_items.append(m)

        # Auto-zoom to fit the journey
        self._zoom_to_positions(list(all_journey_positions.values()))

        bus_count = sum(
            1 for s in journey.segments
            if s.from_stop in self.bus_stop_name_positions
            or s.to_stop in self.bus_stop_name_positions
        )
        self.status_label.setText(
            f"Journey: {journey.origin} → {journey.destination}  ·  "
            f"{journey.num_segments} segments  ·  {bus_count} bus stop(s)"
        )

    def clear_highlight(self):
        """Remove only journey-specific items, leave base stations intact."""
        for item in self._path_items:
            self.scene.removeItem(item)
        self._path_items.clear()
        self.status_label.setText("No journey selected")

    # ── Internal helpers ────────────────────────────────────────────────────────────

    def _add_endpoint_marker(self, pos, color: QColor, size: int):
        r = size / 2
        ellipse = QGraphicsEllipseItem(pos[0] - r, pos[1] - r, size, size)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.GlobalColor.white, 2.5))
        ellipse.setZValue(5)
        self.scene.addItem(ellipse)
        return ellipse

    def _zoom_to_positions(self, positions: list):
        """Pan + zoom to tightly fit a list of (x, y) positions."""
        if not positions:
            return
        PAD = 150
        min_x = min(p[0] for p in positions) - PAD
        min_y = min(p[1] for p in positions) - PAD
        max_x = max(p[0] for p in positions) + PAD
        max_y = max(p[1] for p in positions) + PAD
        self.view.fitInView(
            QRectF(min_x, min_y, max_x - min_x, max_y - min_y),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def _zoom_in(self):
        self.view.scale(1.25, 1.25)

    def _zoom_out(self):
        self.view.scale(1.0 / 1.25, 1.0 / 1.25)

    def _reset_view(self):
        self.view.fitInView(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT,
                            Qt.AspectRatioMode.KeepAspectRatio)
