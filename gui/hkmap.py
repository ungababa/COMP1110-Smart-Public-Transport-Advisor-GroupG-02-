"""
Hong Kong Map Visualization Widget
"""

import os
import csv
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
    'MTR':  QColor(0, 100, 200),
    'Bus':  QColor(0, 150, 50),
    'Walk': QColor(100, 100, 100),
}

def load_station_coords():
    """Load MTR station coordinates from mtr_lines_coords.csv."""
    coords = {}
    csv_paths = [
        Path('data/mtr/mtr_lines_coords.csv'),
        Path('gui/../data/mtr/mtr_lines_coords.csv'),
        Path(__file__).parent.parent / 'data' / 'mtr' / 'mtr_lines_coords.csv',
    ]

    for csv_path in csv_paths:
        if csv_path.exists():
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        station = row['Station'].strip()
                        lat = float(row['Latitude'])
                        lon = float(row['Longitude'])
                        coords[station] = (lat, lon)
                return coords
            except Exception:
                pass
    return {}


STATION_COORDS = load_station_coords()

# ── Map geometry ──────────────────────────────────────────────────────────────
MAP_PIXEL_WIDTH  = 3214
MAP_PIXEL_HEIGHT = 2339

MAP_WEST  = 113.83
MAP_EAST  = 114.44
MAP_NORTH = 22.56
MAP_SOUTH = 22.15


def map_range(lat, lon):
    """Convert lat/lon to pixel coordinates on the map image.

    The +90/+80 offsets were empirically calibrated against the base map PNG:
    they minimise the number of MTR stations whose mapped pixel falls on water.
    (Offset (90, 80) leaves only LOHAS Park borderline — a genuine coastal
    reclaimed-land station — out of all 98 MTR stops.)
    """
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
        
        except Exception:
            pass
    
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
                    if stop_name not in stop_name_coords:
                        stop_name_coords[stop_name] = stop_id_coords[stop_id]
        
        except Exception:
            pass

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
        return important_stops
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        for route_elem in root.findall('RSTOP'):
            stop_id = route_elem.findtext('STOP_ID')
            if stop_id and stop_id in stop_id_coords:
                stop_route_count[stop_id] = stop_route_count.get(stop_id, 0) + 1
        
        MAX_IMPORTANT_STOPS = 300
        sorted_stops = sorted(stop_route_count.items(), key=lambda x: x[1], reverse=True)
        for stop_id, count in sorted_stops[:MAX_IMPORTANT_STOPS]:
            important_stops[stop_id] = count
    
    except Exception:
        pass
    
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
            root / 'data' / 'Hong_Kong_Dark_Map.png',   # primary — dark map in data/
            Path('data/Hong_Kong_Dark_Map.png'),
            Path('Hong_Kong_Dark_Map.png'),
            root / 'Hong_Kong_Dark_Map.png',
            root / 'data' / 'Hong_Kong_Base_Map.png',
            Path('data/Hong_Kong_Base_Map.png'),
            Path('Hong_Kong_Base_Map.png'),
            root / 'Hong_Kong_Base_Map.png',
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    pixmap = QPixmap(str(candidate))
                    bg = self.scene.addPixmap(pixmap)
                    bg.setZValue(-1)
                    return
                except Exception:
                    pass

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

        # Important bus stops — small semi-transparent dots to avoid clutter
        # Only render the top 100 (sorted by route density, already capped in identify_*)
        shown = 0
        for stop_id in self.important_bus_stops:
            if shown >= 100:
                break
            if stop_id in self.bus_stop_positions:
                x, y = self.bus_stop_positions[stop_id]
                size = 5
                ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
                ellipse.setBrush(QBrush(QColor(80, 200, 100, 140)))   # semi-transparent green
                ellipse.setPen(QPen(QColor(255, 255, 255, 80), 0.5))  # faint white ring
                ellipse.setZValue(1)
                self.scene.addItem(ellipse)
                important_bus_count += 1
                shown += 1

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

        # Compute which stops get labels: origin, destination, and interchanges
        # (stops where the route_id or mode changes between consecutive segments)
        label_stops = {journey.origin, journey.destination}
        segs = journey.segments
        for i in range(len(segs) - 1):
            curr, nxt = segs[i], segs[i + 1]
            same_route = (
                curr.route_id is not None
                and curr.route_id == nxt.route_id
                and curr.mode_of_transport == nxt.mode_of_transport
            )
            if not same_route:
                label_stops.add(curr.to_stop)
                label_stops.add(nxt.from_stop)

        # Draw dots for every stop; labels only at interchange/endpoint stops.
        # Labels use a greedy anti-overlap placement: try 6 candidate positions
        # around each dot and pick the first that doesn't collide with an
        # already-placed label.
        placed_rects: list = []   # QRectF of each committed label pill

        for stop_name, (x, y) in all_journey_positions.items():
            is_mtr        = stop_name in STATION_COORDS
            should_label  = stop_name in label_stops

            # Highlight dot — white fill with a coloured ring
            # Interchange/endpoint dots are slightly larger for emphasis
            size = (18 if is_mtr else 13) if should_label else (14 if is_mtr else 9)
            ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
            ellipse.setBrush(QBrush(QColor(255, 255, 255)))
            ring_color = QColor(255, 210, 50) if is_mtr else QColor(255, 140, 0)
            ellipse.setPen(QPen(ring_color, 3 if should_label else 2))
            ellipse.setZValue(3)
            self.scene.addItem(ellipse)
            self._path_items.append(ellipse)

            if should_label:
                # Add the text item first so we get an accurate bounding rect
                text = QGraphicsTextItem(stop_name)
                text.setFont(font)
                text.setDefaultTextColor(QColor(15, 20, 40))
                text.setZValue(4)
                self.scene.addItem(text)

                br   = text.boundingRect()
                lw   = br.width()  + 6
                lh   = br.height() + 2
                pad  = size // 2 + 5   # gap between dot edge and label

                # Six candidate positions: right, left, right-low, left-low,
                # below-centre, above-centre
                candidates = [
                    (x + pad,           y - lh / 2),          # right
                    (x - lw - pad,      y - lh / 2),           # left
                    (x + pad,           y + 4),                # right-low
                    (x - lw - pad,      y + 4),                # left-low
                    (x - lw / 2,        y + pad),              # below
                    (x - lw / 2,        y - lh - pad // 2),   # above
                ]

                lx, ly = candidates[0]   # fallback if all overlap
                for cx, cy in candidates:
                    probe = QRectF(cx - 3, cy - 3, lw + 6, lh + 6)
                    if not any(probe.intersects(pr) for pr in placed_rects):
                        lx, ly = cx, cy
                        break

                placed_rects.append(QRectF(lx - 3, ly - 3, lw + 6, lh + 6))
                text.setPos(lx, ly)

                bg_rect = self.scene.addRect(
                    lx - 1, ly - 1, lw, lh,
                    QPen(Qt.PenStyle.NoPen),
                    QBrush(QColor(255, 255, 255, 200)),
                )
                bg_rect.setZValue(3)
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


    # ── Internal helpers ─────────────────────────────────────────────────────

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

