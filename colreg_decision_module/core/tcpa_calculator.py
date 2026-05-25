"""
TCPA (Time to Closest Point of Approach) Calculator.

This module provides the TCPACalculator class for computing collision risk
parameters between own ship and target vessels.
"""

from typing import List, Tuple, Optional, Dict, Any
import math

from ..models.vessel_model import OwnVessel, TargetVessel
from ..utils.geo_utils import calculate_cpa_parameters, calculate_distance


class TCPAResult:
    """
    Container for TCPA calculation results.
    
    Attributes:
        target_id: ID of the target vessel
        tcpa_minutes: Time to CPA in minutes
        dcpa_nm: Distance at CPA in nautical miles
        range_nm: Current range to target in nautical miles
        bearing_true: True bearing to target in degrees
        relative_bearing: Relative bearing to target in degrees
        collision_risk: Risk level ('high', 'medium', 'low', 'none')
    """
    
    def __init__(
        self,
        target_id: str,
        tcpa_minutes: float,
        dcpa_nm: float,
        range_nm: float,
        bearing_true: float,
        relative_bearing: float
    ):
        self.target_id = target_id
        self.tcpa_minutes = tcpa_minutes
        self.dcpa_nm = dcpa_nm
        self.range_nm = range_nm
        self.bearing_true = bearing_true
        self.relative_bearing = relative_bearing
        self.collision_risk = self._calculate_risk()
    
    def _calculate_risk(self) -> str:
        """Determine collision risk level based on TCPA and DCPA."""
        if self.tcpa_minutes <= 0:
            return "none"  # Moving apart
        
        if self.tcpa_minutes < 10 and self.dcpa_nm < 0.3:
            return "high"
        elif self.tcpa_minutes < 20 and self.dcpa_nm < 0.5:
            return "medium"
        elif self.tcpa_minutes < 30 and self.dcpa_nm < 1.0:
            return "low"
        else:
            return "none"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "target_id": self.target_id,
            "tcpa_minutes": round(self.tcpa_minutes, 2),
            "dcpa_nm": round(self.dcpa_nm, 3),
            "range_nm": round(self.range_nm, 3),
            "bearing_true": round(self.bearing_true, 1),
            "relative_bearing": round(self.relative_bearing, 1),
            "collision_risk": self.collision_risk
        }


class TCPACalculator:
    """
    Calculator for TCPA (Time to Closest Point of Approach) and related parameters.
    
    This class computes collision risk metrics between own ship and multiple
    target vessels, providing essential data for COLREG-72 decision making.
    
    Example:
        >>> calculator = TCPACalculator()
        >>> results = calculator.calculate_all(own_vessel, target_vessels)
        >>> for result in results:
        ...     print(f"{result.target_id}: TCPA={result.tcpa_minutes}min, DCPA={result.dcpa_nm}NM")
    """
    
    def __init__(self, safety_threshold_nm: float = 0.5, max_tcpa_minutes: float = 30.0):
        """
        Initialize TCPA calculator.
        
        Args:
            safety_threshold_nm: Minimum safe DCPA in nautical miles
            max_tcpa_minutes: Maximum TCPA to consider for collision risk
        """
        self.safety_threshold_nm = safety_threshold_nm
        self.max_tcpa_minutes = max_tcpa_minutes
    
    def calculate_single(
        self,
        own_vessel: OwnVessel,
        target_vessel: TargetVessel
    ) -> TCPAResult:
        """
        Calculate TCPA and DCPA for a single target vessel.
        
        Args:
            own_vessel: Own ship with position, course, and speed
            target_vessel: Target vessel with position, course, and speed
            
        Returns:
            TCPAResult object containing all collision risk parameters
        """
        # Calculate CPA parameters
        tcpa, dcpa, _ = calculate_cpa_parameters(
            own_lat=own_vessel.lat,
            own_lon=own_vessel.lon,
            own_course=own_vessel.course,
            own_speed=own_vessel.speed,
            target_lat=target_vessel.lat,
            target_lon=target_vessel.lon,
            target_course=target_vessel.course,
            target_speed=target_vessel.speed
        )
        
        # Calculate current range and bearings
        range_nm = calculate_distance(
            own_vessel.lat, own_vessel.lon,
            target_vessel.lat, target_vessel.lon
        )
        
        from ..utils.geo_utils import calculate_bearing, calculate_relative_bearing
        bearing_true = calculate_bearing(
            own_vessel.lat, own_vessel.lon,
            target_vessel.lat, target_vessel.lon
        )
        relative_bearing = calculate_relative_bearing(own_vessel.course, bearing_true)
        
        return TCPAResult(
            target_id=target_vessel.vessel_id,
            tcpa_minutes=tcpa,
            dcpa_nm=dcpa,
            range_nm=range_nm,
            bearing_true=bearing_true,
            relative_bearing=relative_bearing
        )
    
    def calculate_all(
        self,
        own_vessel: OwnVessel,
        target_vessels: List[TargetVessel]
    ) -> List[TCPAResult]:
        """
        Calculate TCPA and DCPA for multiple target vessels.
        
        Args:
            own_vessel: Own ship with position, course, and speed
            target_vessels: List of target vessels
            
        Returns:
            List of TCPAResult objects sorted by collision risk (highest first)
        """
        results = []
        for target in target_vessels:
            result = self.calculate_single(own_vessel, target)
            results.append(result)
        
        # Sort by risk priority: high > medium > low > none
        risk_order = {"high": 0, "medium": 1, "low": 2, "none": 3}
        results.sort(key=lambda r: (risk_order[r.collision_risk], -r.tcpa_minutes if r.tcpa_minutes > 0 else 0))
        
        return results
    
    def get_high_risk_targets(
        self,
        own_vessel: OwnVessel,
        target_vessels: List[TargetVessel]
    ) -> List[TCPAResult]:
        """
        Filter and return only high-risk targets requiring immediate attention.
        
        Args:
            own_vessel: Own ship with position, course, and speed
            target_vessels: List of target vessels
            
        Returns:
            List of TCPAResult objects for high-risk targets only
        """
        all_results = self.calculate_all(own_vessel, target_vessels)
        return [r for r in all_results if r.collision_risk in ("high", "medium")]
    
    def is_collision_imminent(
        self,
        tcpa_minutes: float,
        dcpa_nm: float
    ) -> bool:
        """
        Determine if collision is imminent based on TCPA and DCPA thresholds.
        
        Args:
            tcpa_minutes: Time to CPA in minutes
            dcpa_nm: Distance at CPA in nautical miles
            
        Returns:
            True if collision is imminent, False otherwise
        """
        if tcpa_minutes <= 0:
            return False
        
        return (tcpa_minutes <= self.max_tcpa_minutes and 
                dcpa_nm < self.safety_threshold_nm)
