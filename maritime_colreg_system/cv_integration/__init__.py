"""
Инициализация пакета cv_integration.
"""

from .processor import (
    CVIntegrationError,
    get_vessel_type_from_cv,
    parse_cv_detections,
    CVProcessor
)

__all__ = [
    'CVIntegrationError',
    'get_vessel_type_from_cv',
    'parse_cv_detections',
    'CVProcessor'
]
