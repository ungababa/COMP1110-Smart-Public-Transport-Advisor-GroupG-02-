"""
Hong Kong Map Visualization Widget — Improved
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QWheelEvent


# ── Transport mode colours ────────────────────────────────────────────────────
MODE_COLORS: dict[str, QColor] = {
    "MTR":            QColor(89,  180, 250),   # blue
    "Bus":            QColor(166, 227, 161),   # green
    "Light Rail":     QColor(250, 179, 135),   # orange
    "Walk":           QColor(166, 173, 200),   # gray
    "Airport Express":QColor(203, 166, 247),   # purple
    "Other":          QColor(200, 200, 200),
}

# ── Hardcoded MTR station lat/lon ─────────────────────────────────────────────
STATION_COORDS: dict[str, tuple[float, float]] = {
    "Admiralty":         (22.2788, 114.1646),
    "Airport":           (22.316,  113.9366),
    "AsiaWorld-Expo":    (22.3218, 113.9412),
    "Austin":            (22.3046, 114.1665),
    "Causeway Bay":      (22.2802, 114.1835),
    "Central":           (22.282,  114.1576),
    "Chai Wan":          (22.2644, 114.2368),
    "Che Kung Temple":   (22.3748, 114.1861),
    "Cheung Sha Wan":    (22.3354, 114.1563),
    "Choi Hung":         (22.3348, 114.2089),
    "City One":          (22.3828, 114.2035),
    "Diamond Hill":      (22.3401, 114.2016),
    "Disneyland Resort": (22.3155, 114.0451),
    "East Tsim Sha Tsui":(22.2955, 114.1754),
    "Fanling":           (22.4921, 114.1387),
    "Fo Tan":            (22.3953, 114.1982),
    "Fortress Hill":     (22.2881, 114.1936),
    "HKU":               (22.2841, 114.1356),
    "Hang Hau":          (22.3156, 114.2644),
    "Heng Fa Chuen":     (22.2769, 114.2398),
    "Heng On":           (22.4174, 114.2258),
    "Hin Keng":          (22.364,  114.1708),
    "Ho Man Tin":        (22.3093, 114.1829),
    "Hong Kong":         (22.285,  114.158 ),
    "Hung Hom":          (22.3029, 114.1816),
    "Jordan":            (22.3049, 114.1718),
    "Kai Tak":           (22.3304, 114.1994),
    "Kam Sheung Road":   (22.4348, 114.0634),
    "Kennedy Town":      (22.2812, 114.1285),
    "Kowloon Bay":       (22.3235, 114.2141),
    "Kowloon Tong":      (22.337,  114.1762),
    "Kowloon":           (22.3049, 114.1615),
    "Kwai Fong":         (22.3569, 114.1279),
    "Kwai Hing":         (22.3632, 114.1312),
    "Kwun Tong":         (22.3121, 114.2265),
    "LOHAS Park":        (22.2957, 114.2689),
    "Lai Chi Kok":       (22.3373, 114.1482),
    "Lai King":          (22.3484, 114.1261),
    "Lam Tin":           (22.3068, 114.233 ),
    "Lei Tung":          (22.2421, 114.1562),
    "Lo Wu":             (22.5283, 114.1134),
    "Lok Fu":            (22.338,  114.1871),
    "Lok Ma Chau":       (22.5144, 114.0657),
    "Long Ping":         (22.4477, 114.0253),
    "Ma On Shan":        (22.4247, 114.2316),
    "Mei Foo":           (22.3381, 114.1376),
    "Mong Kok East":     (22.3222, 114.1728),
    "Mong Kok":          (22.3191, 114.1694),
    "Nam Cheong":        (22.3268, 114.1533),
    "Ngau Tau Kok":      (22.3154, 114.2193),
    "North Point":       (22.2909, 114.2007),
    "Ocean Park":        (22.2486, 114.1743),
    "Olympic":           (22.3178, 114.1602),
    "Po Lam":            (22.3224, 114.258 ),
    "Prince Edward":     (22.3245, 114.1683),
    "Quarry Bay":        (22.2878, 114.2096),
    "Sai Wan Ho":        (22.2816, 114.2224),
    "Sai Ying Pun":      (22.2856, 114.1427),
    "Sha Tin Wai":       (22.3771, 114.195 ),
    "Sha Tin":           (22.3825, 114.1875),
    "Sham Shui Po":      (22.3307, 114.1623),
    "Shau Kei Wan":      (22.2789, 114.2289),
    "Shek Kip Mei":      (22.332,  114.1687),
    "Shek Mun":          (22.3877, 114.2083),
    "Sheung Shui":       (22.5012, 114.128 ),
    "Sheung Wan":        (22.2862, 114.1518),
    "Siu Hong":          (22.412,  113.9786),
    "South Horizons":    (22.2425, 114.1491),
    "Sunny Bay":         (22.3318, 114.0288),
    "Tai Koo":           (22.2846, 114.2161),
    "Tai Po Market":     (22.4446, 114.1706),
    "Tai Shui Hang":     (22.4088, 114.223 ),
    "Tai Wai":           (22.3731, 114.1786),
    "Tai Wo Hau":        (22.3708, 114.125 ),
    "Tai Wo":            (22.4511, 114.1611),
    "Tin Hau":           (22.2827, 114.1917),
    "Tin Shui Wai":      (22.4481, 114.0046),
    "Tiu Keng Leng":     (22.3042, 114.2524),
    "Tseung Kwan O":     (22.3074, 114.26  ),
    "Tsim Sha Tsui":     (22.2973, 114.1722),
    "Tsing Yi":          (22.3584, 114.107 ),
    "Tsuen Wan West":    (22.3686, 114.1098),
    "Tsuen Wan":         (22.3736, 114.1178),
    "Tuen Mun":          (22.3952, 113.9731),
    "Tung Chung":        (22.2893, 113.9416),
    "University":        (22.4134, 114.2102),
    "Wan Chai":          (22.2773, 114.1728),
    "Whampo":            (22.305,  114.1896),
    "Wong Chuk Hang":    (22.248,  114.1681),
    "Wong Tai Sin":      (22.3417, 114.1939),
    "Wu Kai Sha":        (22.4291, 114.2438),
    "Yau Ma Tei":        (22.3129, 114.1707),
    "Yau Tong":          (22.2979, 114.2371),
    "Yuen Long":         (22.4461, 114.0352),
}

# ── Map geometry ──────────────────────────────────────────────────────────────
MAP_PIXEL_WIDTH  = 3214
MAP_PIXEL_HEIGHT = 2339
MAP_WEST  = 113.83
MAP_EAST  = 114.44
MAP_NORTH = 22.56
MAP_SOUTH = 22.15


def map_range(lat: float, lon: float) -> tuple[float, float]:
    """Convert lat/lon → pixel coords on the background map image."""
    x = (lon - MAP_WEST)  / (MAP_EAST  - MAP_WEST)  * MAP_PIXEL_WIDTH  + 85
    y = (MAP_NORTH - lat) / (MAP_NORTH - MAP_SOUTH) * MAP_PIXEL_HEIGHT + 85
    return x, y


# ── Custom QGraphicsView ──────────────────────────────────────────────────────

class _MapView(QGraphicsView):
    """Graphics view that adds scroll-wheel zoom and click-to-select-station."""

    stationClicked = pyqtSignal(str)

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # item → station name mapping, populated by HKMapWidget
        self._station_map: dict = {}
        self._press_pos = None

    # ── Public helpers ────────────────────────────────────────────────────────

    def register_station(self, name: str, item: QGraphicsEllipseItem):
        self._station_map[item] = name

    def clear_stations(self):
        self._station_map.clear()

    # ── Events ────────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        """Scroll-wheel zoom centred on cursor."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Emit stationClicked only when it's a click, not a drag."""
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            delta = event.pos() - self._press_pos
            if delta.manhattanLength() < 6:          # small movement → treat as click
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
    """Full Hong Kong transport map with clickable stations and journey highlighting."""

    stationClicked = pyqtSignal(str)   # emits station name when user clicks a dot

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network          = None
        self.stop_positions:  dict[str, tuple[float, float]] = {}
        self._station_items:  dict[str, QGraphicsEllipseItem] = {}
        self._path_items:     list = []          # highlighted route graphics
        self._setup_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        title = QLabel("🗺  Hong Kong Transport Map")
        title.setStyleSheet("font-size: 13px; font-weight: bold; padding: 2px 4px;")
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

        # Scene + view
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT)

        self.view = _MapView(self.scene)
        self.view.stationClicked.connect(self.stationClicked)
        layout.addWidget(self.view)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(12)
        legend.addWidget(QLabel("Legend:"))
        for mode, color in MODE_COLORS.items():
            if mode == "Other":
                continue
            dot = QLabel("●")
            dot.setStyleSheet(
                f"color: rgb({color.red()},{color.green()},{color.blue()}); font-size: 15px;"
            )
            dot.setToolTip(mode)
            legend.addWidget(dot)
            lbl = QLabel(mode)
            lbl.setStyleSheet("font-size: 11px; color: #a6adc8;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # Status bar
        self.status_label = QLabel("Click a station dot on the map to set it as origin or destination")
        self.status_label.setStyleSheet("font-size: 11px; color: #a6adc8; padding: 2px 4px;")
        layout.addWidget(self.status_label)

        self._load_background()

    def _load_background(self):
        path = "Hong_Kong_Base_Map.png"
        if os.path.exists(path):
            try:
                pixmap = QPixmap(path)
                bg = self.scene.addPixmap(pixmap)
                bg.setZValue(-1)
            except Exception as e:
                print(f"[HKMapWidget] Could not load background: {e}")

    # ── Network rendering ─────────────────────────────────────────────────────

    def set_network(self, network):
        self.network = network
        self._render_stations()

    def _render_stations(self):
        """Draw all known MTR station dots on the map."""
        # Remove old station items
        for item in self._station_items.values():
            self.scene.removeItem(item)
        self._station_items.clear()
        self.stop_positions.clear()
        self.view.clear_stations()

        if not self.network:
            return

        STATION_DOT = 14   # px diameter
        mtr_color = MODE_COLORS["MTR"]

        for stop in self.network.all_stops:
            if stop not in STATION_COORDS:
                continue
            lat, lon = STATION_COORDS[stop]
            x, y = map_range(lat, lon)
            self.stop_positions[stop] = (x, y)

            r = STATION_DOT / 2
            ellipse = QGraphicsEllipseItem(x - r, y - r, STATION_DOT, STATION_DOT)
            ellipse.setBrush(QBrush(mtr_color))
            ellipse.setPen(QPen(QColor(255, 255, 255), 1.5))
            ellipse.setZValue(1)
            ellipse.setToolTip(stop)          # hover tooltip = station name
            self.scene.addItem(ellipse)

            self._station_items[stop] = ellipse
            self.view.register_station(stop, ellipse)

        # Fit to view on first load
        self.view.fitInView(
            0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self.status_label.setText(
            f"Showing {len(self.stop_positions)} stations  ·  "
            "Click a dot to select it  ·  Scroll to zoom  ·  Drag to pan"
        )

    # ── Journey highlighting ──────────────────────────────────────────────────

    def highlight_journey(self, journey):
        """Draw the journey route on the map without re-rendering stations."""
        self.clear_highlight()
        if not journey:
            return

        # Draw coloured segment lines (thicker, mode-coloured, behind station dots)
        for seg in journey.segments:
            fp = self.stop_positions.get(seg.from_stop)
            tp = self.stop_positions.get(seg.to_stop)
            if not (fp and tp):
                continue

            color = MODE_COLORS.get(seg.mode_of_transport, MODE_COLORS["Other"])
            line = QGraphicsLineItem(fp[0], fp[1], tp[0], tp[1])
            line.setPen(QPen(color, 6, Qt.PenStyle.SolidLine,
                             Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            line.setZValue(1.5)       # above map, below station dots
            line.setToolTip(f"{seg.from_stop} → {seg.to_stop}  ({seg.mode_of_transport})")
            self.scene.addItem(line)
            self._path_items.append(line)

        # Origin marker — bright green, larger
        origin_pos = self.stop_positions.get(journey.origin)
        if origin_pos:
            m = self._add_marker(origin_pos, QColor(0, 230, 120), 20,
                                 f"Origin: {journey.origin}")
            self._path_items.append(m)

        # Destination marker — bright red, larger
        dest_pos = self.stop_positions.get(journey.destination)
        if dest_pos:
            m = self._add_marker(dest_pos, QColor(255, 60, 60), 20,
                                 f"Destination: {journey.destination}")
            self._path_items.append(m)

        # Auto-zoom to fit journey
        self._zoom_to_journey(journey)

        self.status_label.setText(
            f"  {journey.origin}  →  {journey.destination}  ·  "
            f"{journey.total_duration} min  ·  ${journey.total_cost:.2f} HKD  ·  "
            f"{journey.num_segments} segment(s)"
        )

    def clear_highlight(self):
        """Remove journey lines/markers without touching station dots."""
        for item in self._path_items:
            self.scene.removeItem(item)
        self._path_items.clear()
        self.status_label.setText(
            "Click a dot to select it  ·  Scroll to zoom  ·  Drag to pan"
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _add_marker(self, pos, color: QColor, size: int, tooltip: str):
        r = size / 2
        ellipse = QGraphicsEllipseItem(pos[0] - r, pos[1] - r, size, size)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(QColor(255, 255, 255), 2.5))
        ellipse.setZValue(3)
        ellipse.setToolTip(tooltip)
        self.scene.addItem(ellipse)
        return ellipse

    def _zoom_to_journey(self, journey):
        """Pan + zoom the view to tightly fit the journey's visible stops."""
        positions = []
        for seg in journey.segments:
            for stop in (seg.from_stop, seg.to_stop):
                if stop in self.stop_positions:
                    positions.append(self.stop_positions[stop])

        if not positions:
            return

        PAD = 120
        min_x = min(p[0] for p in positions) - PAD
        min_y = min(p[1] for p in positions) - PAD
        max_x = max(p[0] for p in positions) + PAD
        max_y = max(p[1] for p in positions) + PAD

        self.view.fitInView(
            QRectF(min_x, min_y, max_x - min_x, max_y - min_y),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def _zoom_in(self):
        self.view.scale(1.3, 1.3)

    def _zoom_out(self):
        self.view.scale(1.0 / 1.3, 1.0 / 1.3)

    def _reset_view(self):
        self.view.fitInView(
            0, 0, MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
