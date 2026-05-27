"""
Инициализация пакета decision_maker.
"""

from .colreg_engine import (
    VesselType,
    EncounterType,
    ManeuverType,
    Signal,
    DecisionResult,
    COLREGDecisionMaker
)

__all__ = [
    'VesselType',
    'EncounterType',
    'ManeuverType',
    'Signal',
    'DecisionResult',
    'COLREGDecisionMaker'
]
