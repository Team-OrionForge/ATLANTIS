"""Geospatial range correction, WGS84 coordinate calculation, and HPI risk scoring engine.

Implements slant-to-ground range Pythagorean correction, haversine geodetic destination point formulas,
shapely-based spatial deduplication, and Hazard Priority Index (HPI) multi-factor risk scoring.
"""

from dataclasses import dataclass
import math
from typing import Any
import numpy as np
from shapely.geometry import Point

from pipeline.constants import DEDUP_BUFFER_M, S_CLASS_MAP, S_ECO_MAP


@dataclass
class HPIResult:
    """Container for Hazard Priority Index evaluation results."""

    score: float
    tier: str
    components: dict[str, float]


def slant_to_ground_range(slant_range_m: float, altitude_m: float) -> float:
    """Calculate ground range R_g from slant range R_s and towfish altitude H.

    Formula:
        R_g = sqrt(R_s^2 - H^2)

    Args:
        slant_range_m: Slant range R_s in meters.
        altitude_m: Towfish altitude H in meters above seabed.

    Returns:
        float: Ground range R_g in meters.

    Raises:
        ValueError: If slant_range_m < altitude_m or negative values provided.
    """
    if slant_range_m < 0 or altitude_m < 0:
        raise ValueError("Slant range and altitude must be non-negative values.")
    if slant_range_m < altitude_m:
        raise ValueError(
            f"Slant range ({slant_range_m:.2f} m) cannot be less than towfish altitude ({altitude_m:.2f} m)."
        )

    rg_squared = slant_range_m**2 - altitude_m**2
    return float(math.sqrt(rg_squared))


def pixel_to_geodetic(
    pixel_x: int,
    pixel_y: int,
    towfish_lat: float,
    towfish_lon: float,
    towfish_heading_deg: float,
    px_to_m_ratio: float = 0.1,
    ground_range_m: float = 0.0,
) -> tuple[float, float]:
    """Convert pixel offset and ground range into WGS84 lat/lon geodetic coordinates.

    Uses a closed-form haversine-based destination point formula given starting lat/lon,
    bearing (heading + pixel offset angle), and total distance.

    Args:
        pixel_x: Pixel x offset relative to nadir line.
        pixel_y: Pixel y offset along track direction.
        towfish_lat: Towfish origin latitude [-90, 90].
        towfish_lon: Towfish origin longitude [-180, 180].
        towfish_heading_deg: Towfish heading angle in degrees clockwise from True North [0, 360).
        px_to_m_ratio: Spatial scale resolution (meters per pixel).
        ground_range_m: Ground range distance to target (m).

    Returns:
        tuple[float, float]: Calculated target (latitude, longitude) in degrees.
    """
    # Calculate along-track and cross-track offset distances in meters
    along_track_m = pixel_y * px_to_m_ratio
    cross_track_m = ground_range_m if ground_range_m > 0 else (pixel_x * px_to_m_ratio)

    total_dist_m = math.hypot(along_track_m, cross_track_m)
    if total_dist_m == 0:
        return (float(towfish_lat), float(towfish_lon))

    # Calculate bearing angle relative to true north
    offset_angle_rad = math.atan2(cross_track_m, along_track_m)
    bearing_rad = math.radians(towfish_heading_deg) + offset_angle_rad

    # WGS84 earth radius in meters
    R_earth = 6371000.0

    lat_rad = math.radians(towfish_lat)
    lon_rad = math.radians(towfish_lon)

    target_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(total_dist_m / R_earth)
        + math.cos(lat_rad) * math.sin(total_dist_m / R_earth) * math.cos(bearing_rad)
    )

    target_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(total_dist_m / R_earth) * math.cos(lat_rad),
        math.cos(total_dist_m / R_earth) - math.sin(lat_rad) * math.sin(target_lat_rad),
    )

    target_lat = math.degrees(target_lat_rad)
    target_lon = math.degrees(target_lon_rad)

    # Normalize longitude to [-180, 180]
    target_lon = (target_lon + 180.0) % 360.0 - 180.0

    return (float(target_lat), float(target_lon))


def simulate_dwithin_dedup(
    detections: list[dict[str, Any]], buffer_m: float = DEDUP_BUFFER_M
) -> list[dict[str, Any]]:
    """Simulate PostGIS ST_DWithin spatial join deduplication using Shapely.

    Groups detections within buffer_m meters of each other (converted using approximate
    1 degree lat ~ 111,000 m scaling) and keeps the highest-confidence candidate in each cluster.

    Args:
        detections: List of detection dictionaries containing 'lat', 'lon', and 'confidence'.
        buffer_m: Radius distance threshold in meters.

    Returns:
        list[dict[str, Any]]: Deduplicated list of detection dictionaries.
    """
    if not detections:
        return []

    # Sort detections by confidence descending
    sorted_dets = sorted(detections, key=lambda d: d.get("confidence", 0.0), reverse=True)
    retained_dets: list[dict[str, Any]] = []
    retained_points: list[Point] = []

    # Meters to degrees conversion factor (~111,000 m per degree latitude)
    deg_buffer = buffer_m / 111000.0

    for det in sorted_dets:
        lat = det.get("lat", 0.0)
        lon = det.get("lon", 0.0)
        pt = Point(lon, lat)

        is_duplicate = False
        for kept_pt in retained_points:
            # Use local Euclidean distance in scaled degree space
            dx = (pt.x - kept_pt.x) * math.cos(math.radians(lat))
            dy = pt.y - kept_pt.y
            dist_deg = math.hypot(dx, dy)

            if dist_deg <= deg_buffer:
                is_duplicate = True
                break

        if not is_duplicate:
            retained_dets.append(det)
            retained_points.append(pt)

    return retained_dets


def compute_hpi(class_name: str, span_m: float, depth_m: float) -> HPIResult:
    """Calculate Hazard Priority Index (HPI) multi-factor risk score and hazard tier band.

    Formula:
        HPI = 0.35 * S_class + 0.25 * S_span + 0.20 * S_depth + 0.20 * S_eco

    Tier Bands:
        HPI >= 0.75         -> CRITICAL
        0.50 <= HPI < 0.75  -> HIGH
        0.25 <= HPI < 0.50  -> MODERATE
        HPI < 0.25          -> LOW

    Args:
        class_name: Target taxonomy class string.
        span_m: Maximum bounding dimension of target in meters.
        depth_m: Estimated physical elevation/height above seabed in meters.

    Returns:
        HPIResult: Calculated score, tier classification string, and sub-score components.
    """
    s_class = S_CLASS_MAP.get(class_name.lower(), 0.3)
    s_span = float(np.clip(span_m / 20.0, 0.0, 1.0))
    s_depth = float(np.clip(depth_m / 10.0, 0.0, 1.0))
    s_eco = S_ECO_MAP.get(class_name.lower(), 0.3)

    hpi_score = 0.35 * s_class + 0.25 * s_span + 0.20 * s_depth + 0.20 * s_eco
    hpi_score = float(np.clip(hpi_score, 0.0, 1.0))

    if hpi_score >= 0.75:
        tier = "CRITICAL"
    elif hpi_score >= 0.50:
        tier = "HIGH"
    elif hpi_score >= 0.25:
        tier = "MODERATE"
    else:
        tier = "LOW"

    components = {
        "S_class": round(s_class, 4),
        "S_span": round(s_span, 4),
        "S_depth": round(s_depth, 4),
        "S_eco": round(s_eco, 4),
    }

    return HPIResult(score=round(hpi_score, 4), tier=tier, components=components)
