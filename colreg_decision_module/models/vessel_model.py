"""
Vessel data models for COLREG-72 decision module.

This module defines the core vessel classes used throughout the decision system,
including base Vessel class and specialized OwnVessel and TargetVessel classes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
import math


class VesselType(Enum):
    """Enumeration of vessel types according to COLREG-72."""
    POWER_DRIVEN = "power_driven"
    SAILING = "sailing"
    FISHING = "fishing"
    NUC = "nuc"  # Not Under Command
    RAM = "ram"  # Restricted Ability to Maneuver
    CBD = "cbd"  # Constrained by Draft
    SEAPLANE = "seaplane"
    UNKNOWN = "unknown"


class VesselStatus(Enum):
    """Operational status of a vessel."""
    UNDERWAY = "underway"
    ANCHORED = "anchored"
    MOORED = "moored"
    AGROUND = "aground"


@dataclass
class Vessel:
    """
    Base class representing a vessel with position, course, and speed.
    
    Attributes:
        vessel_id: Unique identifier for the vessel
        lat: Latitude in degrees (WGS84)
        lon: Longitude in degrees (WGS84)
        course: Course over ground in degrees (0-360, true north)
        speed: Speed over ground in knots
        vessel_type: Type of vessel according to COLREG-72
        status: Current operational status
        length: Length of vessel in meters (optional)
        width: Width of vessel in meters (optional)
    """
    vessel_id: str
    lat: float
    lon: float
    course: float
    speed: float
    vessel_type: VesselType = VesselType.UNKNOWN
    status: VesselStatus = VesselStatus.UNDERWAY
    length: Optional[float] = None
    width: Optional[float] = None
    
    def __post_init__(self):
        """Validate and normalize vessel data after initialization."""
        self.course = self._normalize_course(self.course)
        
    @staticmethod
    def _normalize_course(course: float) -> float:
        """Normalize course to 0-360 range."""
        course = course % 360
        if course < 0:
            course += 360
        return course
    
    def get_position(self) -> Tuple[float, float]:
        """Return vessel position as (lat, lon) tuple."""
        return (self.lat, self.lon)
    
    def get_velocity_components(self) -> Tuple[float, float]:
        """
        Calculate velocity components in knots.
        
        Returns:
            Tuple of (v_north, v_east) velocity components
        """
        course_rad = math.radians(self.course)
        v_north = self.speed * math.cos(course_rad)
        v_east = self.speed * math.sin(course_rad)
        return (v_north, v_east)


@dataclass
class OwnVessel(Vessel):
    """
    Represents the own ship (the vessel from whose perspective decisions are made).
    
    Extends Vessel with additional properties relevant to decision making.
    
    Attributes:
        safety_domain: Safety domain radius in nautical miles (default: 1.0 NM)
        min_safe_dcpa: Minimum safe DCPA in nautical miles (default: 0.5 NM)
        max_tcpa_threshold: Maximum TCPA threshold for collision risk in minutes (default: 20)
        maneuver_capability: Maximum rate of turn in degrees per minute
    """
    safety_domain: float = 1.0
    min_safe_dcpa: float = 0.5
    max_tcpa_threshold: float = 20.0
    maneuver_capability: float = 15.0  # degrees per minute
    
    def __post_init__(self):
        """Initialize own vessel with validation."""
        super().__post_init__()
    
    def is_in_safety_domain(self, target: 'TargetVessel', distance_nm: float) -> bool:
        """Check if target is within own vessel's safety domain."""
        return distance_nm <= self.safety_domain
    
    def requires_action(self, tcpa_minutes: float, dcpa_nm: float) -> bool:
        """
        Determine if collision avoidance action is required.
        
        Args:
            tcpa_minutes: Time to CPA in minutes
            dcpa_nm: Distance at CPA in nautical miles
            
        Returns:
            True if action is required, False otherwise
        """
        if tcpa_minutes <= 0:
            return False  # Targets moving apart
        
        return (tcpa_minutes <= self.max_tcpa_threshold and 
                dcpa_nm < self.min_safe_dcpa)


@dataclass
class TargetVessel(Vessel):
    """
    Represents a target vessel (another vessel in the vicinity).
    
    Extends Vessel with tracking and relative motion information.
    
    Attributes:
        detection_timestamp: Unix timestamp when vessel was detected
        confidence: Detection confidence (0-1) from CV system
        relative_bearing: Bearing relative to own ship's heading (degrees)
        range_nm: Range to target in nautical miles
        bearing_true: True bearing to target in degrees
    """
    detection_timestamp: Optional[float] = None
    confidence: float = 1.0
    relative_bearing: Optional[float] = None
    range_nm: Optional[float] = None
    bearing_true: Optional[float] = None
    
    def __post_init__(self):
        """Initialize target vessel with validation."""
        super().__post_init__()
        if not hasattr(self, 'vessel_id') or self.vessel_id == "":
            self.vessel_id = f"TGT_{id(self)}"
    
    def update_relative_info(self, own_lat: float, own_lon: float, own_course: float):
        """
        Update relative bearing and range based on own ship position.
        
        Args:
            own_lat: Own ship latitude
            own_lon: Own ship longitude
            own_course: Own ship course in degrees
        """
        from ..utils.geo_utils import calculate_distance, calculate_bearing, calculate_relative_bearing
        
        self.range_nm = calculate_distance(own_lat, own_lon, self.lat, self.lon)
        self.bearing_true = calculate_bearing(own_lat, own_lon, self.lat, self.lon)
        self.relative_bearing = calculate_relative_bearing(own_course, self.bearing_true)
