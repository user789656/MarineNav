"""
Инициализация пакета core.
"""

from .geo import GeoPosition, calculate_relative_bearing, normalize_angle, angle_difference
from .collision import CollisionRisk, calculate_tcpa_dcpa, calculate_bearing_and_range, predict_position

__all__ = [
    'GeoPosition',
    'calculate_relative_bearing',
    'normalize_angle',
    'angle_difference',
    'CollisionRisk',
    'calculate_tcpa_dcpa',
    'calculate_bearing_and_range',
    'predict_position'
]
