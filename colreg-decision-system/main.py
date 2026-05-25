"""
COLREG Decision System - Main Application
Точка входа приложения FastAPI
"""

import sys
import os

# Добавляем корень проекта в путь импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import random
from datetime import datetime, timezone

from core.vessel import Vessel, Position, VesselType, VesselStatus
from core.collision import CollisionAnalyzer
from core.decision import COLREGDecisionMaker
from models.cv_integration import CVCoreIntegration
from utils.signals import SignalGenerator


app = FastAPI(
    title="COLREG Decision System",
    description="Система принятия решений для расхождения судов по МППСС-72",
    version="1.0.0"
)

# Инициализация компонентов
collision_analyzer = CollisionAnalyzer()
decision_maker = COLREGDecisionMaker(collision_analyzer)
cv_integration = CVCoreIntegration()
signal_generator = SignalGenerator()


class OwnShipRequest(BaseModel):
    """Запрос с параметрами своего судна"""
    lat: float
    lon: float
    speed: float
    course: float
    vessel_type: str = "power_driven"
    status: str = "underway"
    length: float = 0.0
    name: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Запрос на анализ ситуации"""
    own_ship: OwnShipRequest
    target_vessels: Optional[List[Dict[str, Any]]] = None
    limited_visibility: bool = False


@app.get("/")
async def root():
    """Главная страница - возвращает HTML интерфейс"""
    return FileResponse('frontend/templates/index.html')


@app.get("/api/scenario/{scenario_type}")
async def get_scenario(scenario_type: str):
    """
    Получение预设 сценария для демонстрации
    
    Доступные сценарии:
    - head_on: Лоб в лоб (Правило 14)
    - crossing: Пересечение курсов (Правило 15)
    - overtaking: Обгон (Правило 13)
    """
    # Базовая позиция (Севастополь)
    base_lat = 44.6167
    base_lon = 33.5333
    
    scenarios = {
        'head_on': {
            'own_ship': {
                'lat': base_lat,
                'lon': base_lon,
                'speed': 12.0,
                'course': 0,
                'vessel_type': 'power_driven',
                'name': 'Наше судно'
            },
            'target_vessels': [
                {
                    'id': 'target_1',
                    'lat': base_lat + 0.05,
                    'lon': base_lon,
                    'speed': 10.0,
                    'course': 180,
                    'vessel_type': 'power_driven',
                    'name': 'Встречное судно'
                }
            ]
        },
        'crossing': {
            'own_ship': {
                'lat': base_lat,
                'lon': base_lon,
                'speed': 12.0,
                'course': 0,
                'vessel_type': 'power_driven',
                'name': 'Наше судно'
            },
            'target_vessels': [
                {
                    'id': 'target_1',
                    'lat': base_lat + 0.03,
                    'lon': base_lon + 0.03,
                    'speed': 8.0,
                    'course': 270,
                    'vessel_type': 'power_driven',
                    'name': 'Судно справа'
                }
            ]
        },
        'overtaking': {
            'own_ship': {
                'lat': base_lat,
                'lon': base_lon,
                'speed': 15.0,
                'course': 45,
                'vessel_type': 'power_driven',
                'name': 'Наше судно'
            },
            'target_vessels': [
                {
                    'id': 'target_1',
                    'lat': base_lat + 0.02,
                    'lon': base_lon + 0.02,
                    'speed': 8.0,
                    'course': 45,
                    'vessel_type': 'power_driven',
                    'name': 'Медленное судно'
                }
            ]
        }
    }
    
    if scenario_type not in scenarios:
        raise HTTPException(
            status_code=404,
            detail=f"Сценарий '{scenario_type}' не найден. Доступные: {list(scenarios.keys())}"
        )
    
    return scenarios[scenario_type]


@app.post("/api/analyze")
async def analyze_situation(request: AnalyzeRequest):
    """
    Анализ ситуации и получение рекомендаций по расхождению
    
    Принимает параметры своего судна и опционально список целевых судов.
    Если целевые суда не указаны, генерируются тестовые данные.
    """
    # Создание объекта своего судна
    own_ship = Vessel(
        id="own_ship",
        position=Position(lat=request.own_ship.lat, lon=request.own_ship.lon),
        speed=request.own_ship.speed,
        course=request.own_ship.course,
        vessel_type=VesselType(request.own_ship.vessel_type),
        status=VesselStatus(request.own_ship.status),
        length=request.own_ship.length,
        name=request.own_ship.name or "Наше судно"
    )
    
    # Генерация или использование предоставленных целевых судов
    target_ships = []
    
    if request.target_vessels:
        for tv in request.target_vessels:
            target_ships.append(Vessel(
                id=tv.get('id', f"target_{random.randint(1000, 9999)}"),
                position=Position(lat=tv['lat'], lon=tv['lon']),
                speed=tv.get('speed', 10.0),
                course=tv.get('course', 0),
                vessel_type=VesselType(tv.get('vessel_type', 'power_driven')),
                status=VesselStatus(tv.get('status', 'underway')),
                length=tv.get('length', 0.0),
                name=tv.get('name')
            ))
    else:
        # Генерация тестовых судов на основе позиции своего судна
        target_ships = generate_test_targets(own_ship)
    
    # Принятие решения
    decision = decision_maker.make_decision(
        own_ship=own_ship,
        target_ships=target_ships,
        limited_visibility=request.limited_visibility
    )
    
    # Формирование ответа
    target_vessels_data = []
    analysis = collision_analyzer.analyze_all_targets(own_ship, target_ships)
    
    for target_id, result in analysis.items():
        target = result['vessel']
        risk = result['collision_risk']
        
        target_vessels_data.append({
            'id': target.id,
            'name': target.name,
            'lat': target.position.lat,
            'lon': target.position.lon,
            'speed': target.speed,
            'course': target.course,
            'vessel_type': target.vessel_type.value,
            'distance': risk.distance,
            'tcpa': risk.tcpa,
            'dcpa': risk.dcpa,
            'risk_level': risk.risk_level
        })
    
    # Преобразование действий в словарь
    actions_data = []
    for action in decision.actions:
        actions_data.append({
            'maneuver_type': action.maneuver_type.value if action.maneuver_type else None,
            'description': action.description,
            'rule_number': action.rule_number,
            'sound_signal': action.sound_signal,
            'light_signal': action.light_signal,
            'priority': action.priority,
            'target_vessel_id': action.target_vessel_id
        })
    
    return {
        'situation_summary': decision.situation_summary,
        'has_collision_risk': decision.has_collision_risk,
        'warnings': decision.warnings,
        'actions': actions_data,
        'target_vessels': target_vessels_data,
        'own_ship': {
            'lat': own_ship.position.lat,
            'lon': own_ship.position.lon,
            'speed': own_ship.speed,
            'course': own_ship.course,
            'vessel_type': own_ship.vessel_type.value
        }
    }


def generate_test_targets(own_ship: Vessel) -> List[Vessel]:
    """
    Генерация тестовых целевых судов для демонстрации
    
    Создает несколько судов с различными ситуациями встречи
    """
    targets = []
    base_lat = own_ship.position.lat
    base_lon = own_ship.position.lon
    
    # Судно 1: Лоб в лоб
    targets.append(Vessel(
        id="target_headon",
        position=Position(lat=base_lat + 0.05, lon=base_lon),
        speed=10.0,
        course=180,
        vessel_type=VesselType.POWER_DRIVEN,
        name="Встречное судно"
    ))
    
    # Судно 2: Пересечение справа
    targets.append(Vessel(
        id="target_crossing",
        position=Position(lat=base_lat + 0.03, lon=base_lon + 0.03),
        speed=8.0,
        course=270,
        vessel_type=VesselType.POWER_DRIVEN,
        name="Судно справа"
    ))
    
    # Судно 3: Обгоняемое
    targets.append(Vessel(
        id="target_overtake",
        position=Position(lat=base_lat + 0.02, lon=base_lon + 0.02),
        speed=6.0,
        course=45,
        vessel_type=VesselType.SAILING,
        name="Парусное судно"
    ))
    
    # Судно 4: Рыболовное (имеет приоритет)
    targets.append(Vessel(
        id="target_fishing",
        position=Position(lat=base_lat - 0.02, lon=base_lon + 0.04),
        speed=3.0,
        course=90,
        vessel_type=VesselType.FISHING,
        name="Рыболовное судно"
    ))
    
    return targets


@app.get("/api/signals")
async def get_signals_info():
    """Получение информации о всех сигналах МППСС-72"""
    sound_signals = SoundSignals.get_all_maneuver_signals()
    light_signals = LightSignals.get_all_maneuver_lights()
    
    return {
        'sound_signals': {
            key: signal_generator.generate_signal_display(signal)
            for key, signal in sound_signals.items()
        },
        'light_signals': {
            key: signal_generator.generate_signal_display(signal)
            for key, signal in light_signals.items()
        },
        'vessel_lights': {
            vtype: signal_generator.get_vessel_lights_display(vtype)
            for vtype in ['power_driven', 'sailing', 'fishing', 'nuc', 'ram', 'cbd']
        }
    }


# Импорт здесь чтобы избежать циклического импорта
from utils.signals import SoundSignals, LightSignals

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
