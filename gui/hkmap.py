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
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QFont


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
    x = (lon - MAP_WEST) / (MAP_EAST - MAP_WEST) * MAP_PIXEL_WIDTH + 75
    y = (MAP_NORTH - lat) / (MAP_NORTH - MAP_SOUTH) * MAP_PIXEL_HEIGHT + 75
    return x, y


def load_bus_stops():
    """Load bus stop coordinates from STOP_BUS.xml and RSTOP_BUS.xml.
    
    Returns:
        Tuple: (stop_id_coords_dict, stop_name_coords_dict)
        - stop_id_coords: stop_id -> (lat, lon)
        - stop_name_coords: stop_name -> (lat, lon) for journeys
    """
    stop_id_coords = {}
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
    """Identify important bus stations based on route density.
    
    Analyzes RSTOP_BUS.xml to count how many routes pass through each stop.
    Returns the top 300 busiest interchanges.
    
    Args:
        stop_id_coords: Dictionary of stop_id -> (lat, lon)
    
    Returns:
        Dict: stop_id -> route_count for top 300 important stops
    """
    important_stops = {}
    stop_route_count = {}
    
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


class HKMapWidget(QWidget):
    """Widget for displaying Hong Kong transport map."""

    stationClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = None
        self.stop_positions = {}
        self.highlighted_path = []
        
        # Load bus stop data
        self.bus_stops_by_id, self.bus_stops_by_name = load_bus_stops()
        self.important_bus_stops = identify_important_bus_stations(self.bus_stops_by_id)
        self.bus_stop_positions = {}  # stop_id -> (x, y) pixel coordinates
        self.bus_stop_name_positions = {}  # stop_name -> (x, y) pixel coordinates
        self.journey_bus_stops = set()  # stop_names in current journey
        
        # Pre-compute pixel coordinates for all bus stops
        for stop_id, (lat, lon) in self.bus_stops_by_id.items():
            x, y = map_range(lat, lon)
            self.bus_stop_positions[stop_id] = (x, y)
        
        for stop_name, (lat, lon) in self.bus_stops_by_name.items():
            x, y = map_range(lat, lon)
            self.bus_stop_name_positions[stop_name] = (x, y)
        
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
            img_paths = [
                Path('data/Hong_Kong_Base_Map.png'),
                Path(__file__).parent.parent / 'data' / 'Hong_Kong_Base_Map.png',
            ]
            img_file = None
            for p in img_paths:
                if p.exists():
                    img_file = p
                    break
            if img_file:
                pixmap = QPixmap(str(img_file))
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

        mtr_count = 0
        important_bus_count = 0
        self.journey_bus_stops.clear()

        # Render MTR stations
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
                mtr_count += 1

        # Render important bus stops (always visible)
        for stop_id in self.important_bus_stops.keys():
            if stop_id in self.bus_stop_positions:
                x, y = self.bus_stop_positions[stop_id]
                
                # Important bus stops: small blue dots
                size = 8
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(QColor(0, 100, 200)))  # Blue
                ellipse.setPen(QPen(Qt.GlobalColor.white, 1))
                ellipse.setZValue(1)
                self.scene.addItem(ellipse)
                important_bus_count += 1

        self.status_label.setText(
            f"Showing {mtr_count} MTR stations + {important_bus_count} important bus interchanges"
        )

    def highlight_journey(self, journey):
        if not journey:
            return

        self._render_stations()
        self.highlighted_path = journey.segments

        prev_pos = None
        journey_bus_stops_found = set()
        all_journey_stops = {}  # stop_name -> position for labeling
        
        for seg in journey.segments:
            from_pos = self.stop_positions.get(seg.from_stop)
            to_pos = self.stop_positions.get(seg.to_stop)

            if from_pos and to_pos:
                # Both are MTR stations
                line = QGraphicsLineItem(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                line.setPen(QPen(QColor(255, 0, 0), 3))
                line.setZValue(2)
                self.scene.addItem(line)
                all_journey_stops[seg.from_stop] = from_pos
                all_journey_stops[seg.to_stop] = to_pos
                prev_pos = to_pos
            elif from_pos:
                # from_stop is MTR, to_stop is not
                ellipse = QGraphicsEllipseItem(from_pos[0] - 6, from_pos[1] - 6, 12, 12)
                ellipse.setBrush(QBrush(QColor(0, 200, 0)))
                ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
                ellipse.setZValue(2)
                self.scene.addItem(ellipse)
                all_journey_stops[seg.from_stop] = from_pos
                prev_pos = from_pos
                
                # Check if to_stop is a bus stop
                if seg.to_stop in self.bus_stop_name_positions:
                    to_pos = self.bus_stop_name_positions[seg.to_stop]
                    journey_bus_stops_found.add(seg.to_stop)
                    all_journey_stops[seg.to_stop] = to_pos
            else:
                # from_stop is not in MTR stations, check if it's a bus stop
                from_pos = None
                if seg.from_stop in self.bus_stop_name_positions:
                    from_pos = self.bus_stop_name_positions[seg.from_stop]
                    journey_bus_stops_found.add(seg.from_stop)
                    all_journey_stops[seg.from_stop] = from_pos
                
                # to_stop is not in MTR stations, check if it's a bus stop
                to_pos = None
                if seg.to_stop in self.bus_stop_name_positions:
                    to_pos = self.bus_stop_name_positions[seg.to_stop]
                    journey_bus_stops_found.add(seg.to_stop)
                    all_journey_stops[seg.to_stop] = to_pos
                
                # If both are bus stops, draw a line
                if from_pos and to_pos:
                    line = QGraphicsLineItem(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
                    line.setPen(QPen(QColor(255, 0, 0), 3))
                    line.setZValue(2)
                    self.scene.addItem(line)
                    prev_pos = to_pos

        # Render all stops in the journey with labels
        font = QFont()
        font.setPointSize(8)
        
        for stop_name, (x, y) in all_journey_stops.items():
            if stop_name in STATION_COORDS:
                # MTR station - already rendered, just add label
                size = 6
            else:
                # Bus stop - render green dot
                size = 6
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(QColor(0, 150, 50)))  # Green
                ellipse.setPen(QPen(Qt.GlobalColor.white, 1))
                ellipse.setZValue(2)
                self.scene.addItem(ellipse)
            
            # Add station name label to the right of the point
            text_item = QGraphicsTextItem(stop_name)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(0, 0, 0))
            text_item.setPos(x + 10, y - 8)  # Position to the right and slightly up
            text_item.setZValue(3)  # Above everything else
            self.scene.addItem(text_item)

        # Mark endpoint if needed
        if prev_pos:
            ellipse = QGraphicsEllipseItem(prev_pos[0] - 6, prev_pos[1] - 6, 12, 12)
            ellipse.setBrush(QBrush(QColor(255, 0, 0)))
            ellipse.setPen(QPen(Qt.GlobalColor.white, 2))
            ellipse.setZValue(2)
            self.scene.addItem(ellipse)

        bus_stop_count = len(journey_bus_stops_found)
        self.status_label.setText(
            f"Journey: {journey.origin} → {journey.destination} "
            f"({journey.num_segments} segments, {bus_stop_count} bus stops)"
        )

    def _zoom_in(self):
        self.view.scale(1.2, 1.2)

    def _zoom_out(self):
        self.view.scale(0.8, 0.8)

    def _reset_view(self):
        self.view.resetTransform()
        self._render_stations()