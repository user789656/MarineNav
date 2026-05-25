"""
Signal Generator for COLREG-72 light and sound signals.

This module generates appropriate visual (light) and auditory (sound) signals
based on vessel type, status, and maneuver actions as required by COLREG-72.
"""

from typing import List, Dict, Any, Optional
from enum import Enum

from ..models.vessel_model import VesselType, VesselStatus


class SignalType(Enum):
    """Types of signals."""
    LIGHT = "light"
    SOUND = "sound"
    DAY_SHAPE = "day_shape"


class LightSignal:
    """
    Represents a navigational light signal.
    
    Attributes:
        color: Color of the light (white, red, green, yellow)
        arc: Arc of visibility in degrees
        range_nm: Visible range in nautical miles
        position: Position on vessel (mast, port, starboard, stern)
        characteristic: Light characteristic (fixed, flashing, occulting)
    """
    
    def __init__(
        self,
        color: str,
        arc: int,
        range_nm: float,
        position: str,
        characteristic: str = "fixed"
    ):
        self.color = color
        self.arc = arc
        self.range_nm = range_nm
        self.position = position
        self.characteristic = characteristic
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "color": self.color,
            "arc_degrees": self.arc,
            "range_nm": self.range_nm,
            "position": self.position,
            "characteristic": self.characteristic,
            "type": "light"
        }


class SoundSignal:
    """
    Represents a sound signal.
    
    Attributes:
        duration: Duration type ('short' ~1s, 'prolonged' ~4-6s)
        count: Number of blasts
        interval: Interval between blasts in seconds
        meaning: Human-readable meaning of the signal
    """
    
    def __init__(
        self,
        duration: str,
        count: int = 1,
        interval: float = 1.0,
        meaning: str = ""
    ):
        self.duration = duration
        self.count = count
        self.interval = interval
        self.meaning = meaning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "duration": self.duration,
            "count": self.count,
            "interval_seconds": self.interval,
            "meaning": self.meaning,
            "type": "sound"
        }


class DayShape:
    """
    Represents a day shape signal.
    
    Attributes:
        shape: Shape type (ball, cone, cylinder, diamond)
        count: Number of shapes
        arrangement: Vertical arrangement description
        meaning: Human-readable meaning
    """
    
    def __init__(
        self,
        shape: str,
        count: int = 1,
        arrangement: str = "",
        meaning: str = ""
    ):
        self.shape = shape
        self.count = count
        self.arrangement = arrangement
        self.meaning = meaning
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "shape": self.shape,
            "count": self.count,
            "arrangement": self.arrangement,
            "meaning": self.meaning,
            "type": "day_shape"
        }


class SignalGenerator:
    """
    Generator for COLREG-72 compliant light, sound, and day shape signals.
    
    This class provides methods to generate appropriate signals based on:
    1. Vessel type and status (Rules 23-31)
    2. Maneuver actions (Rule 34)
    3. Restricted visibility conditions (Rule 35)
    4. Distress situations (Annex IV)
    
    Example:
        >>> generator = SignalGenerator()
        >>> lights = generator.get_lights_for_vessel(VesselType.POWER_DRIVEN, VesselStatus.UNDERWAY)
        >>> print(f"Required lights: {[l.to_dict() for l in lights]}")
    """
    
    # Standard visibility ranges based on vessel size (Rule 22)
    RANGE_LARGE = 6.0  # Vessels >= 50m - masthead light
    RANGE_MEDIUM = 5.0  # Vessels 12-50m - masthead light
    RANGE_SMALL = 2.0  # Vessels < 12m
    RANGE_SIDE = 3.0  # Side lights for large vessels
    RANGE_SIDE_MEDIUM = 2.0  # Side lights for medium vessels
    
    def __init__(self, vessel_length: float = 20.0):
        """
        Initialize signal generator.
        
        Args:
            vessel_length: Length of own vessel in meters (affects light ranges)
        """
        self.vessel_length = vessel_length
        self._set_ranges()
    
    def _set_ranges(self):
        """Set appropriate light ranges based on vessel length."""
        if self.vessel_length >= 50:
            self.masthead_range = self.RANGE_LARGE
            self.side_range = self.RANGE_SIDE
        elif self.vessel_length >= 12:
            self.masthead_range = self.RANGE_MEDIUM
            self.side_range = self.RANGE_SIDE_MEDIUM
        else:
            self.masthead_range = self.RANGE_SMALL
            self.side_range = self.RANGE_SMALL
    
    def get_lights_for_vessel(
        self,
        vessel_type: VesselType,
        status: VesselStatus,
        underway: bool = True
    ) -> List[LightSignal]:
        """
        Get required navigation lights for a vessel type and status.
        
        Args:
            vessel_type: Type of vessel
            status: Operational status
            underway: Whether vessel is underway (vs anchored/moored)
            
        Returns:
            List of LightSignal objects
        """
        if status == VesselStatus.ANCHORED:
            return self._get_anchored_lights()
        
        if vessel_type == VesselType.POWER_DRIVEN:
            return self._get_power_driven_lights(underway)
        elif vessel_type == VesselType.SAILING:
            return self._get_sailing_lights(underway)
        elif vessel_type == VesselType.FISHING:
            return self._get_fishing_lights()
        elif vessel_type == VesselType.NUC:
            return self._get_nuc_lights(underway)
        elif vessel_type == VesselType.RAM:
            return self._get_ram_lights(underway)
        elif vessel_type == VesselType.CBD:
            return self._get_cbd_lights(underway)
        else:
            return self._get_power_driven_lights(underway)  # Default
    
    def _get_power_driven_lights(self, underway: bool) -> List[LightSignal]:
        """Get lights for power-driven vessel (Rule 23)."""
        lights = []
        
        # Masthead light (forward)
        lights.append(LightSignal(
            color="white",
            arc=225,
            range_nm=self.masthead_range,
            position="forward_mast",
            characteristic="fixed"
        ))
        
        # Second masthead light if >= 50m (abaft and higher)
        if self.vessel_length >= 50:
            lights.append(LightSignal(
                color="white",
                arc=225,
                range_nm=self.masthead_range,
                position="aft_mast_higher",
                characteristic="fixed"
            ))
        
        if underway:
            # Sidelights
            lights.append(LightSignal(
                color="green",
                arc=112.5,
                range_nm=self.side_range,
                position="starboard",
                characteristic="fixed"
            ))
            lights.append(LightSignal(
                color="red",
                arc=112.5,
                range_nm=self.side_range,
                position="port",
                characteristic="fixed"
            ))
            
            # Sternlight
            lights.append(LightSignal(
                color="white",
                arc=135,
                range_nm=self.side_range,
                position="stern",
                characteristic="fixed"
            ))
        
        return lights
    
    def _get_sailing_lights(self, underway: bool) -> List[LightSignal]:
        """Get lights for sailing vessel (Rule 25)."""
        lights = []
        
        if underway:
            # Sidelights and sternlight
            lights.append(LightSignal(
                color="green",
                arc=112.5,
                range_nm=self.side_range,
                position="starboard",
                characteristic="fixed"
            ))
            lights.append(LightSignal(
                color="red",
                arc=112.5,
                range_nm=self.side_range,
                position="port",
                characteristic="fixed"
            ))
            lights.append(LightSignal(
                color="white",
                arc=135,
                range_nm=self.side_range,
                position="stern",
                characteristic="fixed"
            ))
            
            # Optional: Red over green at masthead
            lights.append(LightSignal(
                color="red",
                arc=360,
                range_nm=self.side_range,
                position="masthead_upper",
                characteristic="fixed"
            ))
            lights.append(LightSignal(
                color="green",
                arc=360,
                range_nm=self.side_range,
                position="masthead_lower",
                characteristic="fixed"
            ))
        
        return lights
    
    def _get_fishing_lights(self) -> List[LightSignal]:
        """Get lights for fishing vessel (Rule 26)."""
        lights = []
        
        # Red over white all-round
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_upper",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="white",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_lower",
            characteristic="fixed"
        ))
        
        # Additional lights when making way
        lights.extend(self._get_power_driven_lights(underway=True))
        
        return lights
    
    def _get_nuc_lights(self, underway: bool) -> List[LightSignal]:
        """Get lights for vessel Not Under Command (Rule 27)."""
        lights = []
        
        # Two red all-round lights in vertical line
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_upper",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_lower",
            characteristic="fixed"
        ))
        
        if underway:
            lights.extend(self._get_power_driven_lights(underway=True)[2:])  # Sidelights and stern
        
        return lights
    
    def _get_ram_lights(self, underway: bool) -> List[LightSignal]:
        """Get lights for vessel Restricted Ability to Maneuver (Rule 27)."""
        lights = []
        
        # Red-white-red all-round in vertical line
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_upper",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="white",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_middle",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_lower",
            characteristic="fixed"
        ))
        
        if underway:
            lights.extend(self._get_power_driven_lights(underway=True)[2:])
        
        return lights
    
    def _get_cbd_lights(self, underway: bool) -> List[LightSignal]:
        """Get lights for vessel Constrained by Draft (Rule 28)."""
        lights = self._get_power_driven_lights(underway)
        
        # Three red all-round lights in vertical line (in addition)
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_highest",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_middle",
            characteristic="fixed"
        ))
        lights.append(LightSignal(
            color="red",
            arc=360,
            range_nm=self.masthead_range,
            position="masthead_lower",
            characteristic="fixed"
        ))
        
        return lights
    
    def _get_anchored_lights(self) -> List[LightSignal]:
        """Get lights for anchored vessel (Rule 30)."""
        lights = []
        
        # White all-round forward
        lights.append(LightSignal(
            color="white",
            arc=360,
            range_nm=self.side_range,
            position="forward",
            characteristic="fixed"
        ))
        
        # White all-round aft (lower) if >= 50m
        if self.vessel_length >= 50:
            lights.append(LightSignal(
                color="white",
                arc=360,
                range_nm=self.side_range,
                position="aft_lower",
                characteristic="fixed"
            ))
        
        return lights
    
    def get_maneuver_sound_signal(self, maneuver_type: str) -> SoundSignal:
        """
        Get sound signal for a maneuver (Rule 34).
        
        Args:
            maneuver_type: Type of maneuver
            
        Returns:
            SoundSignal object
        """
        if maneuver_type == "starboard":
            return SoundSignal(
                duration="short",
                count=1,
                interval=0,
                meaning="I am altering my course to starboard"
            )
        elif maneuver_type == "port":
            return SoundSignal(
                duration="short",
                count=2,
                interval=1.0,
                meaning="I am altering my course to port"
            )
        elif maneuver_type == "astern":
            return SoundSignal(
                duration="short",
                count=3,
                interval=1.0,
                meaning="I am operating astern propulsion"
            )
        elif maneuver_type == "doubt":
            return SoundSignal(
                duration="short",
                count=5,
                interval=0.5,
                meaning="I doubt whether sufficient action is being taken"
            )
        else:
            return SoundSignal(
                duration="short",
                count=1,
                interval=0,
                meaning="Standard signal"
            )
    
    def get_day_shapes_for_vessel(
        self,
        vessel_type: VesselType,
        status: VesselStatus
    ) -> List[DayShape]:
        """
        Get day shapes for a vessel type and status.
        
        Args:
            vessel_type: Type of vessel
            status: Operational status
            
        Returns:
            List of DayShape objects
        """
        if status == VesselStatus.ANCHORED:
            return [DayShape(
                shape="ball",
                count=1,
                arrangement="forward",
                meaning="Vessel at anchor"
            )]
        
        if vessel_type == VesselType.NUC:
            return [DayShape(
                shape="ball",
                count=2,
                arrangement="vertical line",
                meaning="Not Under Command"
            )]
        elif vessel_type == VesselType.RAM:
            return [DayShape(
                shape="ball",
                count=1,
                arrangement="upper",
                meaning="Restricted Ability to Maneuver (partial)"
            ), DayShape(
                shape="diamond",
                count=1,
                arrangement="middle",
                meaning="Restricted Ability to Maneuver"
            ), DayShape(
                shape="ball",
                count=1,
                arrangement="lower",
                meaning="Restricted Ability to Maneuver (partial)"
            )]
        elif vessel_type == VesselType.FISHING:
            return [DayShape(
                shape="cone",
                count=2,
                arrangement="apexes together (vertical)",
                meaning="Vessel engaged in fishing"
            )]
        elif vessel_type == VesselType.CBD:
            return [DayShape(
                shape="cylinder",
                count=1,
                arrangement="",
                meaning="Constrained by Draft"
            )]
        elif vessel_type == VesselType.SAILING:
            # Cone apex down if under sail and power
            return [DayShape(
                shape="cone",
                count=1,
                arrangement="apex down",
                meaning="Motor-sailing"
            )]
        
        return []
    
    def get_fog_signal(
        self,
        vessel_type: VesselType,
        underway: bool,
        making_way: bool
    ) -> SoundSignal:
        """
        Get fog signal for restricted visibility (Rule 35).
        
        Args:
            vessel_type: Type of vessel
            underway: Whether vessel is underway
            making_way: Whether vessel is making way through water
            
        Returns:
            SoundSignal object
        """
        if not underway:
            # At anchor
            return SoundSignal(
                duration="prolonged",
                count=1,
                interval=60.0,
                meaning="Vessel at anchor - bell signal"
            )
        
        if vessel_type == VesselType.POWER_DRIVEN:
            if making_way:
                return SoundSignal(
                    duration="prolonged",
                    count=1,
                    interval=120.0,  # Every 2 minutes
                    meaning="Power-driven vessel making way"
                )
            else:
                return SoundSignal(
                    duration="prolonged",
                    count=2,
                    interval=120.0,
                    meaning="Power-driven vessel stopped, no way"
                )
        
        # NUC, RAM, Fishing, Sailing, etc.
        return SoundSignal(
            duration="prolonged",
            count=1,
            interval=120.0,
            meaning="Followed by two short blasts"
        )
