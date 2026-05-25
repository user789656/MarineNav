"""
Vessel data models for COLREG-72 decision module.
Defines vessel types, states, and properties.
"""

from .vessel_model import Vessel, OwnVessel, TargetVessel, VesselType, VesselStatus

__all__ = [
    "Vessel",
    "OwnVessel", 
    "TargetVessel",
    "VesselType",
    "VesselStatus",
]
