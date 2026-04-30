"""Transform HK1980 grid coordinates in STOP_BUS_1.xml to WGS84 geographic coordinates.

This script reads the bus stop XML, converts each <X>/<Y> pair from HK1980
Grid Coordinates to WGS84 (ITRF96) geographic coordinates via the Hong Kong
Geodetic Survey Section coordinate transformation API, and writes the
latitude/longitude values back into the same XML tags.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET


API_URL = "http://www.geodetic.gov.hk/transform/v2/"
DEFAULT_INPUT = Path("bus") / "STOP_BUS_1.xml"


def fetch_wgs84_coordinates(easting: str, northing: str) -> Tuple[float, float]:
    """Convert one HK1980 grid coordinate pair to WGS84 latitude/longitude."""

    query = urlencode(
        {
            "inSys": "hkgrid",
            "outSys": "wgsgeog",
            "e": easting,
            "n": northing,
        }
    )
    request_url = f"{API_URL}?{query}"

    try:
        with urlopen(request_url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Geodetic API returned HTTP {exc.code} for {easting}, {northing}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach the Geodetic API: {exc.reason}") from exc

    error_code = payload.get("ErrorCode")
    if error_code is not None:
        raise RuntimeError(
            f"Geodetic API rejected coordinate ({easting}, {northing}) with ErrorCode {error_code}"
        )

    try:
        latitude = float(payload["wgsLat"])
        longitude = float(payload["wgsLong"])
    except KeyError as exc:
        raise RuntimeError(
            f"Geodetic API response did not include WGS84 coordinates for ({easting}, {northing})"
        ) from exc

    return latitude, longitude


def transform_stop_file(input_path: Path, output_path: Path | None = None, precision: int = 4) -> int:
    """Transform every stop in the XML and write the updated document."""

    tree = ET.parse(input_path)
    root = tree.getroot()
    cache: Dict[Tuple[str, str], Tuple[float, float]] = {}
    transformed_count = 0

    for stop in root.findall("STOP"):
        x_node = stop.find("X")
        y_node = stop.find("Y")
        if x_node is None or y_node is None or x_node.text is None or y_node.text is None:
            continue

        easting = x_node.text.strip()
        northing = y_node.text.strip()
        cache_key = (easting, northing)

        if cache_key not in cache:
            cache[cache_key] = fetch_wgs84_coordinates(easting, northing)

        latitude, longitude = cache[cache_key]
        x_node.text = f"{latitude:.{precision}f}"
        y_node.text = f"{longitude:.{precision}f}"
        transformed_count += 1

    ET.indent(tree, space="  ")

    destination = output_path or input_path
    if destination == input_path:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(input_path.parent), suffix=".xml") as tmp:
            tree.write(tmp, encoding="utf-8", xml_declaration=True)
            temp_path = Path(tmp.name)
        temp_path.replace(input_path)
    else:
        tree.write(destination, encoding="utf-8", xml_declaration=True)

    return transformed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform STOP_BUS_1.xml X/Y values from HK1980 grid coordinates to WGS84 latitude/longitude."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help="Path to the input XML file (default: bus/STOP_BUS_1.xml)",
    )
    parser.add_argument(
        "--output",
        help="Optional output file. If omitted, the input file is updated in place.",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=4,
        help="Decimal places to write for latitude and longitude (default: 4)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        transformed_count = transform_stop_file(input_path, output_path=output_path, precision=args.precision)
    except Exception as exc:
        print(f"Transformation failed: {exc}", file=sys.stderr)
        return 1

    target = output_path if output_path is not None else input_path
    print(f"Transformed {transformed_count} stops and wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())