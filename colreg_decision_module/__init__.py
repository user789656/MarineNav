"""
COLREG-72 Decision Module for Maritime Navigation
==================================================

A comprehensive module for vessel collision avoidance decision-making
based on International Regulations for Preventing Collisions at Sea (COLREG-72).

This module calculates TCPA (Time to Closest Point of Approach), DCPA (Distance at CPA),
determines encounter situations, and provides maneuver recommendations with appropriate
light and sound signals.

Author: Maritime AI Team
Version: 1.0.0
"""

from .core.tcpa_calculator import TCPACalculator
from .core.encounter_classifier import EncounterClassifier
from .core.decision_engine import COLREGDecisionEngine
from .core.signal_generator import SignalGenerator
from .models.vessel_model import Vessel, OwnVessel, TargetVessel
from .utils.geo_utils import calculate_distance, calculate_bearing, haversine_distance

__version__ = "1.0.0"
__all__ = [
    "TCPACalculator",
    "EncounterClassifier", 
    "COLREGDecisionEngine",
    "SignalGenerator",
    "Vessel",
    "OwnVessel",
    "TargetVessel",
    "calculate_distance",
    "calculate_bearing",
    "haversine_distance",
]
