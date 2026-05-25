"""
COLREG Decision System - Models Module
Интеграция с ML моделями и cv-core
"""

from .cv_integration import CVCoreIntegration, VesselDetectionResult

__all__ = ['CVCoreIntegration', 'VesselDetectionResult']
