"""
Geographic utility functions for maritime navigation calculations.

This module provides essential geospatial calculations including distance,
bearing, and relative motion computations used throughout the COLREG
decision system.
"""

import math
from typing import Tuple


# Earth's radius in nautical miles
EARTH_RADIUS_NM = 3440.065  # 6371 km / 1.852


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees
        
    Returns:
        Distance between points in nautical miles
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_NM * c


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic positions.
    
    This is an alias for haversine_distance for API consistency.
    
    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees
        
    Returns:
        Distance between points in nautical miles
    """
    return haversine_distance(lat1, lon1, lat2, lon2)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial bearing from point 1 to point 2.
    
    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees
        
    Returns:
        Bearing in degrees (0-360, true north)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    return normalize_angle(bearing_deg)


def calculate_relative_bearing(own_course: float, target_bearing: float) -> float:
    """
    Calculate the relative bearing of a target from own ship's heading.
    
    Relative bearing is measured clockwise from own ship's bow (0° = dead ahead,
    90° = starboard beam, 180° = dead astern, 270° = port beam).
    
    Args:
        own_course: Own ship's course over ground in degrees
        target_bearing: True bearing to target in degrees
        
    Returns:
        Relative bearing in degrees (0-360)
    """
    relative = target_bearing - own_course
    return normalize_angle(relative)


def normalize_angle(angle: float) -> float:
    """
    Normalize an angle to the range [0, 360).
    
    Args:
        angle: Angle in degrees (can be any value)
        
    Returns:
        Normalized angle in degrees (0-360)
    """
    angle = angle % 360
    if angle < 0:
        angle += 360
    return angle


def knots_to_mps(speed_knots: float) -> float:
    """
    Convert speed from knots to meters per second.
    
    Args:
        speed_knots: Speed in knots
        
    Returns:
        Speed in meters per second
    """
    return speed_knots * 0.514444


def mps_to_knots(speed_mps: float) -> float:
    """
    Convert speed from meters per second to knots.
    
    Args:
        speed_mps: Speed in meters per second
        
    Returns:
        Speed in knots
    """
    return speed_mps / 0.514444


def calculate_cpa_parameters(
    own_lat: float, own_lon: float, own_course: float, own_speed: float,
    target_lat: float, target_lon: float, target_course: float, target_speed: float
) -> Tuple[float, float, float]:
    """
    Calculate CPA (Closest Point of Approach) parameters.
    
    This function computes TCPA, DCPA, and range to CPA using relative motion analysis.
    
    Args:
        own_lat: Own ship latitude in degrees
        own_lon: Own ship longitude in degrees
        own_course: Own ship course in degrees
        own_speed: Own ship speed in knots
        target_lat: Target ship latitude in degrees
        target_lon: Target ship longitude in degrees
        target_course: Target ship course in degrees
        target_speed: Target ship speed in knots
        
    Returns:
        Tuple of (tcpa_minutes, dcpa_nm, range_to_cpa_nm):
            - tcpa_minutes: Time to CPA (negative if already past CPA)
            - dcpa_nm: Distance at CPA in nautical miles
            - range_to_cpa_nm: Current range to CPA point
    """
    # Convert to radians
    own_course_rad = math.radians(own_course)
    target_course_rad = math.radians(target_course)
    
    # Calculate velocity components (in knots)
    own_v_north = own_speed * math.cos(own_course_rad)
    own_v_east = own_speed * math.sin(own_course_rad)
    target_v_north = target_speed * math.cos(target_course_rad)
    target_v_east = target_speed * math.sin(target_course_rad)
    
    # Relative velocity (target relative to own)
    rel_v_north = target_v_north - own_v_north
    rel_v_east = target_v_east - own_v_east
    
    # Relative position (target relative to own)
    # Approximate conversion: 1 degree lat ≈ 60 NM, 1 degree lon ≈ 60 * cos(lat) NM
    avg_lat = (own_lat + target_lat) / 2
    lat_scale = 60.0
    lon_scale = 60.0 * math.cos(math.radians(avg_lat))
    
    rel_pos_north = (target_lat - own_lat) * lat_scale
    rel_pos_east = (target_lon - own_lon) * lon_scale
    
    # Relative speed squared
    rel_speed_sq = rel_v_north ** 2 + rel_v_east ** 2
    
    if rel_speed_sq < 1e-10:
        # Vessels have nearly identical velocity - no relative motion
        current_range = math.sqrt(rel_pos_north ** 2 + rel_pos_east ** 2)
        return (float('inf'), current_range, current_range)
    
    # Time to CPA (in hours)
    tcpa_hours = -(rel_pos_north * rel_v_north + rel_pos_east * rel_v_east) / rel_speed_sq
    
    # Position at CPA (relative)
    cpa_pos_north = rel_pos_north + tcpa_hours * rel_v_north
    cpa_pos_east = rel_pos_east + tcpa_hours * rel_v_east
    
    # DCPA (distance at CPA)
    dcpa_nm = math.sqrt(cpa_pos_north ** 2 + cpa_pos_east ** 2)
    
    # Range to CPA point from current position
    range_to_cpa = abs(tcpa_hours) * math.sqrt(rel_speed_sq)
    
    # Convert TCPA to minutes
    tcpa_minutes = tcpa_hours * 60
    
    return (tcpa_minutes, dcpa_nm, range_to_cpa)
