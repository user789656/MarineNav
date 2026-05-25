"""
COLREG-72 Decision Engine.

This module provides the main decision-making logic for collision avoidance,
integrating TCPA calculations, encounter classification, and COLREG rules
to generate maneuver recommendations.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.vessel_model import OwnVessel, TargetVessel, VesselType
from .tcpa_calculator import TCPACalculator, TCPAResult
from .encounter_classifier import EncounterClassifier, EncounterType, GiveWayResponsibility


class ManeuverType(Enum):
    """Types of collision avoidance maneuvers."""
    ALTER_COURSE_STARBOARD = "alter_course_starboard"
    ALTER_COURSE_PORT = "alter_course_port"
    REDUCE_SPEED = "reduce_speed"
    STOP_ENGINES = "stop_engines"
    REVERSE_ENGINES = "reverse_engines"
    MAINTAIN_COURSE_SPEED = "maintain_course_speed"
    MONITOR_SITUATION = "monitor_situation"


@dataclass
class DecisionResult:
    """
    Container for a complete decision result for a target vessel.
    
    Attributes:
        target_id: ID of the target vessel
        encounter_type: Type of encounter situation
        responsibility: Give-way responsibility
        tcpa_result: TCPA calculation results
        recommended_maneuver: Recommended action
        maneuver_angle: Suggested course change in degrees (if applicable)
        signals_required: List of required light/sound signals
        urgency: Urgency level ('immediate', 'soon', 'monitor', 'none')
        reasoning: Human-readable explanation of the decision
    """
    target_id: str
    encounter_type: EncounterType
    responsibility: GiveWayResponsibility
    tcpa_result: TCPAResult
    recommended_maneuver: ManeuverType
    maneuver_angle: Optional[float]
    signals_required: List[str]
    urgency: str
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision result to dictionary for JSON serialization."""
        return {
            "target_id": self.target_id,
            "encounter_type": self.encounter_type.value,
            "responsibility": self.responsibility.value,
            "tcpa_result": self.tcpa_result.to_dict(),
            "recommended_maneuver": self.recommended_maneuver.value,
            "maneuver_angle": self.maneuver_angle,
            "signals_required": self.signals_required,
            "urgency": self.urgency,
            "reasoning": self.reasoning
        }


class COLREGDecisionEngine:
    """
    Main decision engine implementing COLREG-72 collision avoidance logic.
    
    This engine integrates:
    1. TCPA/DCPA calculations for collision risk assessment
    2. Encounter situation classification
    3. Vessel type priority rules (Rule 18)
    4. Maneuver recommendations with appropriate signals
    
    Example:
        >>> engine = COLREGDecisionEngine()
        >>> decisions = engine.make_decisions(own_vessel, target_vessels)
        >>> for decision in decisions:
        ...     print(f"{decision.target_id}: {decision.recommended_maneuver.value}")
        ...     print(f"  Signals: {decision.signals_required}")
    """
    
    # Minimum course alteration for effective maneuver (Rule 8)
    MIN_COURSE_CHANGE = 30.0  # degrees
    
    # Speed reduction thresholds
    SPEED_REDUCTION_FACTOR = 0.5  # Reduce to 50% of current speed
    
    def __init__(self):
        """Initialize the decision engine with required components."""
        self.tcpa_calculator = TCPACalculator()
        self.classifier = EncounterClassifier()
    
    def make_decisions(
        self,
        own_vessel: OwnVessel,
        target_vessels: List[TargetVessel]
    ) -> List[DecisionResult]:
        """
        Make collision avoidance decisions for all target vessels.
        
        Args:
            own_vessel: Own ship with position, course, speed, and type
            target_vessels: List of target vessels with their parameters
            
        Returns:
            List of DecisionResult objects sorted by urgency
        """
        decisions = []
        
        # Calculate TCPA for all targets
        tcpa_results = self.tcpa_calculator.calculate_all(own_vessel, target_vessels)
        
        # Create a mapping for quick lookup
        tcpa_map = {r.target_id: r for r in tcpa_results}
        
        # Process each target
        for target in target_vessels:
            tcpa_result = tcpa_map.get(target.vessel_id)
            if not tcpa_result:
                continue
            
            # Classify encounter
            encounter_type, responsibility = self.classifier.classify(
                own_vessel, target, tcpa_result.relative_bearing
            )
            
            # Generate decision
            decision = self._generate_decision(
                own_vessel, target, encounter_type, responsibility, tcpa_result
            )
            decisions.append(decision)
        
        # Sort by urgency
        urgency_order = {"immediate": 0, "soon": 1, "monitor": 2, "none": 3}
        decisions.sort(key=lambda d: urgency_order[d.urgency])
        
        return decisions
    
    def _generate_decision(
        self,
        own_vessel: OwnVessel,
        target: TargetVessel,
        encounter_type: EncounterType,
        responsibility: GiveWayResponsibility,
        tcpa_result: TCPAResult
    ) -> DecisionResult:
        """
        Generate a specific decision for a target vessel.
        
        Args:
            own_vessel: Own ship parameters
            target: Target vessel parameters
            encounter_type: Classified encounter type
            responsibility: Give-way responsibility
            tcpa_result: TCPA calculation results
            
        Returns:
            DecisionResult with maneuver recommendation and signals
        """
        # Determine urgency based on TCPA
        urgency = self._determine_urgency(tcpa_result)
        
        # Check if action is required
        requires_action = own_vessel.requires_action(
            tcpa_result.tcpa_minutes, tcpa_result.dcpa_nm
        )
        
        # Determine maneuver based on responsibility and encounter
        if not requires_action or responsibility == GiveWayResponsibility.OWN_STAND_ON:
            maneuver, angle, reasoning = self._stand_on_action(encounter_type, tcpa_result)
            signals = []
        elif responsibility == GiveWayResponsibility.BOTH_RESTRICTED:
            maneuver, angle, reasoning = self._both_restricted_action(tcpa_result)
            signals = ["white_light_all_round"]  # NUC/RAM signal
        else:
            # We must give way
            maneuver, angle, reasoning = self._give_way_action(
                own_vessel, target, encounter_type, tcpa_result
            )
            signals = self._get_maneuver_signals(maneuver, angle)
        
        return DecisionResult(
            target_id=target.vessel_id,
            encounter_type=encounter_type,
            responsibility=responsibility,
            tcpa_result=tcpa_result,
            recommended_maneuver=maneuver,
            maneuver_angle=angle,
            signals_required=signals,
            urgency=urgency,
            reasoning=reasoning
        )
    
    def _determine_urgency(self, tcpa_result: TCPAResult) -> str:
        """Determine urgency level based on TCPA and DCPA."""
        if tcpa_result.collision_risk == "high":
            return "immediate"
        elif tcpa_result.collision_risk == "medium":
            return "soon"
        elif tcpa_result.collision_risk == "low":
            return "monitor"
        else:
            return "none"
    
    def _stand_on_action(
        self,
        encounter_type: EncounterType,
        tcpa_result: TCPAResult
    ) -> Tuple[ManeuverType, Optional[float], str]:
        """
        Determine action when we are the stand-on vessel (Rule 17).
        
        Rule 17(a)(i): Maintain course and speed
        Rule 17(a)(ii): May take action if give-way vessel doesn't act
        Rule 17(b): Must take action when collision cannot be avoided by give-way vessel alone
        Rule 17(c): Avoid altering to port for vessel on our port side
        """
        if tcpa_result.tcpa_minutes <= 0:
            return (
                ManeuverType.MONITOR_SITUATION,
                None,
                "Vessels moving apart - no action required"
            )
        
        if tcpa_result.dcpa_nm >= 0.5:
            return (
                ManeuverType.MAINTAIN_COURSE_SPEED,
                None,
                "Safe DCPA - maintain course and speed per Rule 17(a)(i)"
            )
        
        # If DCPA is unsafe and TCPA is short, we may need to take action
        if tcpa_result.tcpa_minutes < 10:
            if encounter_type == EncounterType.CROSSING_PORT:
                # Avoid port turn for vessel on port side (Rule 17c)
                return (
                    ManeuverType.REDUCE_SPEED,
                    None,
                    "Close quarters - reduce speed while maintaining course per Rule 17(b)"
                )
            else:
                return (
                    ManeuverType.ALTER_COURSE_STARBOARD,
                    self.MIN_COURSE_CHANGE,
                    "Close quarters - alter course to starboard per Rule 17(b)"
                )
        
        return (
            ManeuverType.MONITOR_SITUATION,
            None,
            "Stand-on vessel - monitor give-way vessel's actions per Rule 17(a)"
        )
    
    def _give_way_action(
        self,
        own_vessel: OwnVessel,
        target: TargetVessel,
        encounter_type: EncounterType,
        tcpa_result: TCPAResult
    ) -> Tuple[ManeuverType, Optional[float], str]:
        """
        Determine action when we are the give-way vessel.
        
        Rules:
        - Rule 13: Overtaking vessel keeps clear
        - Rule 14: Head-on - both alter to starboard
        - Rule 15: Crossing - give way to vessel on starboard side
        - Rule 16: Take early and substantial action
        """
        if encounter_type == EncounterType.HEAD_ON:
            # Rule 14: Both vessels alter course to starboard
            return (
                ManeuverType.ALTER_COURSE_STARBOARD,
                max(self.MIN_COURSE_CHANGE, 45.0),
                "Head-on situation - alter course to starboard per Rule 14"
            )
        
        elif encounter_type == EncounterType.CROSSING_STARBOARD:
            # Rule 15: We give way to vessel on our starboard side
            # Best action: Alter to starboard to pass astern
            return (
                ManeuverType.ALTER_COURSE_STARBOARD,
                max(self.MIN_COURSE_CHANGE, 60.0),
                "Crossing with vessel on starboard - alter to starboard to pass astern per Rule 15"
            )
        
        elif encounter_type == EncounterType.OVERTAKING:
            # Rule 13: Overtaking vessel keeps clear
            # Can alter either way, but starboard is preferred
            return (
                ManeuverType.ALTER_COURSE_STARBOARD,
                self.MIN_COURSE_CHANGE,
                "Overtaking situation - keep clear of overtaken vessel per Rule 13"
            )
        
        elif encounter_type == EncounterType.CROSSING_PORT:
            # This shouldn't happen if classification is correct
            # But handle as precaution
            return (
                ManeuverType.MONITOR_SITUATION,
                None,
                "Vessel on port side - typically we are stand-on, verify situation"
            )
        
        # Default case
        return (
            ManeuverType.REDUCE_SPEED,
            None,
            "Unclear situation - reduce speed and assess per Rule 8(e)"
        )
    
    def _both_restricted_action(
        self,
        tcpa_result: TCPAResult
    ) -> Tuple[ManeuverType, Optional[float], str]:
        """
        Determine action when both vessels are restricted (NUC, RAM).
        
        In this case, standard rules don't apply directly.
        Focus on minimizing risk through speed reduction and careful maneuvering.
        """
        if tcpa_result.tcpa_minutes < 10:
            return (
                ManeuverType.STOP_ENGINES,
                None,
                "Both vessels restricted - stop engines to assess situation per Rule 2(b)"
            )
        else:
            return (
                ManeuverType.REDUCE_SPEED,
                None,
                "Both vessels restricted - reduce speed and communicate per Rule 2(b)"
            )
    
    def _get_maneuver_signals(
        self,
        maneuver: ManeuverType,
        angle: Optional[float]
    ) -> List[str]:
        """
        Get required sound/light signals for a maneuver (Rule 34).
        
        Sound signals:
        - 1 short blast: Altering course to starboard
        - 2 short blasts: Altering course to port
        - 3 short blasts: Operating astern propulsion
        
        Light signals (optional, same pattern):
        - 1 flash: Starboard
        - 2 flashes: Port
        - 3 flashes: Astern
        """
        signals = []
        
        if maneuver == ManeuverType.ALTER_COURSE_STARBOARD:
            signals.extend([
                "sound_one_short_blast",
                "light_one_flash_starboard"
            ])
        elif maneuver == ManeuverType.ALTER_COURSE_PORT:
            signals.extend([
                "sound_two_short_blasts",
                "light_two_flashes_port"
            ])
        elif maneuver in (ManeuverType.STOP_ENGINES, ManeuverType.REVERSE_ENGINES):
            signals.extend([
                "sound_three_short_blasts",
                "light_three_flashes_astern"
            ])
        
        return signals
    
    def get_emergency_signal(self) -> Dict[str, Any]:
        """
        Return emergency/distress signal information (Rule 37, Annex IV).
        
        Returns:
            Dictionary with emergency signal details
        """
        return {
            "sound_signals": [
                "gun_or_explosive_at_1min_intervals",
                "continuous_foghorn",
                "sos_in_morse (...---...)"
            ],
            "visual_signals": [
                "red_star_shells",
                "orange_smoke",
                "flames_on_vessel",
                "square_flag_with_ball"
            ],
            "radio_signals": [
                "MAYDAY_voice",
                "SOS_radiotelegraphy",
                "NC_flags"
            ]
        }
