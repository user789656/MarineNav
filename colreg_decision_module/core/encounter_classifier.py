"""
Encounter Situation Classifier for COLREG-72.

This module classifies vessel encounter situations (head-on, crossing, overtaking)
based on relative bearing and other parameters as defined in COLREG-72.
"""

from typing import Tuple, Optional
from enum import Enum

from ..models.vessel_model import VesselType, TargetVessel, OwnVessel


class EncounterType(Enum):
    """Types of vessel encounters according to COLREG-72."""
    HEAD_ON = "head_on"
    CROSSING_STARBOARD = "crossing_starboard"  # Target on starboard side
    CROSSING_PORT = "crossing_port"  # Target on port side
    OVERTAKING = "overtaking"
    TARGET_OVERTAKING_US = "target_overtaking_us"  # We are being overtaken
    PARALLEL_OPPOSITE = "parallel_opposite"  # Moving parallel in opposite direction
    PARALLEL_SAME = "parallel_same"  # Moving parallel in same direction
    UNKNOWN = "unknown"


class GiveWayResponsibility(Enum):
    """Who has the give-way responsibility in an encounter."""
    OWN_GIVE_WAY = "own_give_way"  # Own ship must give way
    OWN_STAND_ON = "own_stand_on"  # Own ship is stand-on vessel
    BOTH_RESTRICTED = "both_restricted"  # Both vessels restricted (e.g., NUC, RAM)
    UNCLEAR = "unclear"


class EncounterClassifier:
    """
    Classifier for vessel encounter situations based on COLREG-72 rules.
    
    This class analyzes relative motion parameters and vessel types to determine:
    1. The type of encounter (head-on, crossing, overtaking)
    2. Which vessel has give-way responsibility
    3. Priority based on vessel types (Rule 18)
    
    Example:
        >>> classifier = EncounterClassifier()
        >>> encounter_type, responsibility = classifier.classify(own_vessel, target_vessel, relative_bearing)
        >>> print(f"Encounter: {encounter_type.value}, Responsibility: {responsibility.value}")
    """
    
    # Angular thresholds for encounter classification (degrees)
    HEAD_ON_THRESHOLD = 22.5  # ±22.5° from bow for head-on
    OVERTAKING_THRESHOLD = 67.5  # ±67.5° from stern for overtaking ( abaft the beam)
    
    def __init__(self):
        """Initialize the encounter classifier."""
        pass
    
    def classify(
        self,
        own_vessel: OwnVessel,
        target_vessel: TargetVessel,
        relative_bearing: float
    ) -> Tuple[EncounterType, GiveWayResponsibility]:
        """
        Classify the encounter situation between own ship and a target vessel.
        
        Args:
            own_vessel: Own ship with course and speed
            target_vessel: Target vessel with course and speed
            relative_bearing: Relative bearing to target (0-360°, 0=dead ahead)
            
        Returns:
            Tuple of (EncounterType, GiveWayResponsibility)
        """
        # Determine encounter type based on relative bearing
        encounter_type = self._determine_encounter_type(
            own_vessel.course, own_vessel.speed,
            target_vessel.course, target_vessel.speed,
            relative_bearing
        )
        
        # Determine give-way responsibility
        responsibility = self._determine_responsibility(
            own_vessel.vessel_type, target_vessel.vessel_type, encounter_type
        )
        
        return (encounter_type, responsibility)
    
    def _determine_encounter_type(
        self,
        own_course: float,
        own_speed: float,
        target_course: float,
        target_speed: float,
        relative_bearing: float
    ) -> EncounterType:
        """
        Determine the type of encounter based on geometry and relative motion.
        
        Args:
            own_course: Own ship course in degrees
            own_speed: Own ship speed in knots
            target_course: Target ship course in degrees
            target_speed: Target ship speed in knots
            relative_bearing: Relative bearing to target in degrees
            
        Returns:
            EncounterType enum value
        """
        import math
        
        # Normalize angles
        rel_bearing = relative_bearing % 360
        
        # Calculate course difference
        course_diff = abs((target_course - own_course + 180) % 360 - 180)
        
        # Check for overtaking (target behind our beam - Rule 13)
        # Overtaking: more than 22.5° abaft the beam (> 112.5° from bow)
        if rel_bearing > 112.5 and rel_bearing < 247.5:
            # We are overtaking the target
            if own_speed > target_speed:
                return EncounterType.OVERTAKING
            else:
                return EncounterType.TARGET_OVERTAKING_US
        
        # Check for head-on or nearly head-on (Rule 14)
        # Head-on: target within ±22.5° of our bow, courses nearly opposite
        if rel_bearing <= self.HEAD_ON_THRESHOLD or rel_bearing >= 360 - self.HEAD_ON_THRESHOLD:
            if course_diff > 157.5:  # Courses nearly opposite (within 22.5° of 180°)
                return EncounterType.HEAD_ON
        
        # Crossing situations (Rule 15)
        if course_diff > 45:  # Not roughly parallel
            if 0 < rel_bearing <= 112.5:
                # Target on our starboard side
                return EncounterType.CROSSING_STARBOARD
            elif 247.5 <= rel_bearing < 360:
                # Target on our port side
                return EncounterType.CROSSING_PORT
        
        # Parallel courses
        if course_diff <= 22.5:
            return EncounterType.PARALLEL_SAME
        elif course_diff >= 157.5:
            return EncounterType.PARALLEL_OPPOSITE
        
        return EncounterType.UNKNOWN
    
    def _determine_responsibility(
        self,
        own_type: VesselType,
        target_type: VesselType,
        encounter_type: EncounterType
    ) -> GiveWayResponsibility:
        """
        Determine give-way responsibility based on vessel types and encounter.
        
        Priority hierarchy (Rule 18) - highest to lowest:
        1. NUC (Not Under Command)
        2. RAM (Restricted Ability to Maneuver)
        3. CBD (Constrained by Draft)
        4. FISHING
        5. SAILING
        6. POWER_DRIVEN
        
        Args:
            own_type: Type of own vessel
            target_type: Type of target vessel
            encounter_type: Type of encounter situation
            
        Returns:
            GiveWayResponsibility enum value
        """
        # Priority values (lower = higher priority)
        priority = {
            VesselType.NUC: 0,
            VesselType.RAM: 1,
            VesselType.CBD: 2,
            VesselType.FISHING: 3,
            VesselType.SAILING: 4,
            VesselType.POWER_DRIVEN: 5,
            VesselType.SEAPLANE: 6,
            VesselType.UNKNOWN: 7
        }
        
        own_priority = priority.get(own_type, 7)
        target_priority = priority.get(target_type, 7)
        
        # Special cases where both vessels are restricted
        if own_type in (VesselType.NUC, VesselType.RAM) and target_type in (VesselType.NUC, VesselType.RAM):
            return GiveWayResponsibility.BOTH_RESTRICTED
        
        # If target has higher priority (lower number), we give way
        if target_priority < own_priority:
            return GiveWayResponsibility.OWN_GIVE_WAY
        
        # If we have higher priority, we are stand-on
        if own_priority < target_priority:
            return GiveWayResponsibility.OWN_STAND_ON
        
        # Same priority - use encounter type rules
        return self._apply_encounter_rules(encounter_type)
    
    def _apply_encounter_rules(self, encounter_type: EncounterType) -> GiveWayResponsibility:
        """
        Apply COLREG-72 encounter-specific rules for same-priority vessels.
        
        Rules:
        - Head-on (Rule 14): Both alter course to starboard
        - Crossing (Rule 15): Give-way to vessel on starboard side
        - Overtaking (Rule 13): Overtaking vessel keeps clear
        
        Args:
            encounter_type: Type of encounter situation
            
        Returns:
            GiveWayResponsibility enum value
        """
        if encounter_type == EncounterType.HEAD_ON:
            # Both vessels should alter course to starboard
            return GiveWayResponsibility.OWN_GIVE_WAY  # We take action
        
        elif encounter_type == EncounterType.CROSSING_STARBOARD:
            # Target is on our starboard side - we give way (Rule 15)
            return GiveWayResponsibility.OWN_GIVE_WAY
        
        elif encounter_type == EncounterType.CROSSING_PORT:
            # Target is on our port side - we are stand-on (Rule 15)
            return GiveWayResponsibility.OWN_STAND_ON
        
        elif encounter_type == EncounterType.OVERTAKING:
            # We are overtaking - we keep clear (Rule 13)
            return GiveWayResponsibility.OWN_GIVE_WAY
        
        elif encounter_type == EncounterType.TARGET_OVERTAKING_US:
            # Target is overtaking us - they keep clear (Rule 13)
            return GiveWayResponsibility.OWN_STAND_ON
        
        # Default: maintain vigilance
        return GiveWayResponsibility.UNCLEAR
    
    def get_relative_bearing_sector(self, relative_bearing: float) -> str:
        """
        Get the sector name for a given relative bearing.
        
        Sectors:
        - Dead Ahead: 0° (±11.25°)
        - Starboard Bow: 11.25° - 67.5°
        - Starboard Beam: 67.5° - 112.5°
        - Starboard Quarter: 112.5° - 157.5°
        - Dead Astern: 180° (±22.5°)
        - Port Quarter: 202.5° - 247.5°
        - Port Beam: 247.5° - 292.5°
        - Port Bow: 292.5° - 348.75°
        
        Args:
            relative_bearing: Relative bearing in degrees (0-360)
            
        Returns:
            Sector name string
        """
        bearing = relative_bearing % 360
        
        if bearing <= 11.25 or bearing >= 348.75:
            return "Dead Ahead"
        elif bearing <= 67.5:
            return "Starboard Bow"
        elif bearing <= 112.5:
            return "Starboard Beam"
        elif bearing <= 157.5:
            return "Starboard Quarter"
        elif bearing <= 202.5:
            return "Dead Astern"
        elif bearing <= 247.5:
            return "Port Quarter"
        elif bearing <= 292.5:
            return "Port Beam"
        elif bearing <= 348.75:
            return "Port Bow"
        else:
            return "Unknown"
