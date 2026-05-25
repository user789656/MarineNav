"""
Тестовый скрипт для проверки работы COLREG Decision System
Демонстрирует расчет TCPA/DCPA и принятие решений по МППСС-72
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.vessel import Vessel, Position, VesselType, VesselStatus
from core.collision import CollisionAnalyzer
from core.decision import COLREGDecisionMaker


def test_tcpa_dcpa_calculation():
    """Тест расчета TCPA и DCPA"""
    print("=" * 60)
    print("ТЕСТ 1: Расчет TCPA/DCPA")
    print("=" * 60)
    
    analyzer = CollisionAnalyzer()
    
    # Свое судно
    own_ship = Vessel(
        id="own",
        position=Position(lat=44.6167, lon=33.5333),
        speed=12.0,
        course=0,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    # Целевое судно - лоб в лоб
    target = Vessel(
        id="target",
        position=Position(lat=44.6667, lon=33.5333),  # ~5 миль на север
        speed=10.0,
        course=180,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    risk = analyzer.calculate_tcpa_dcpa(own_ship, target)
    
    print(f"Дистанция: {risk.distance:.2f} миль")
    print(f"TCPA: {risk.tcpa:.1f} мин")
    print(f"DCPA: {risk.dcpa:.2f} миль")
    print(f"Уровень риска: {risk.risk_level}")
    print(f"Опасность: {'ДА' if risk.is_risk else 'НЕТ'}")
    print()


def test_encounter_classification():
    """Тест классификации ситуаций встречи"""
    print("=" * 60)
    print("ТЕСТ 2: Классификация ситуаций встречи")
    print("=" * 60)
    
    analyzer = CollisionAnalyzer()
    
    own_ship = Vessel(
        id="own",
        position=Position(lat=44.6167, lon=33.5333),
        speed=12.0,
        course=0,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    # Сценарий 1: Лоб в лоб
    target_headon = Vessel(
        id="headon",
        position=Position(lat=44.6667, lon=33.5333),
        speed=10.0,
        course=180,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    encounter = analyzer.classify_encounter(own_ship, target_headon)
    print(f"Сценарий 1 (Лоб в лоб):")
    print(f"  Тип: {encounter.situation_type}")
    print(f"  Правило: {encounter.applicable_rule}")
    print(f"  Описание: {encounter.description}")
    print()
    
    # Сценарий 2: Пересечение справа
    target_crossing = Vessel(
        id="crossing",
        position=Position(lat=44.6467, lon=33.5633),
        speed=8.0,
        course=270,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    encounter = analyzer.classify_encounter(own_ship, target_crossing)
    print(f"Сценарий 2 (Пересечение справа):")
    print(f"  Тип: {encounter.situation_type}")
    print(f"  Правило: {encounter.applicable_rule}")
    print(f"  Описание: {encounter.description}")
    print()
    
    # Сценарий 3: Обгон
    target_overtake = Vessel(
        id="overtake",
        position=Position(lat=44.6367, lon=33.5533),
        speed=6.0,
        course=45,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    encounter = analyzer.classify_encounter(own_ship, target_overtake)
    print(f"Сценарий 3 (Обгон):")
    print(f"  Тип: {encounter.situation_type}")
    print(f"  Правило: {encounter.applicable_rule}")
    print(f"  Описание: {encounter.description}")
    print()


def test_decision_making():
    """Тест принятия решений"""
    print("=" * 60)
    print("ТЕСТ 3: Принятие решений по МППСС-72")
    print("=" * 60)
    
    decision_maker = COLREGDecisionMaker()
    
    own_ship = Vessel(
        id="own",
        position=Position(lat=44.6167, lon=33.5333),
        speed=12.0,
        course=0,
        vessel_type=VesselType.POWER_DRIVEN,
        name="Наше судно"
    )
    
    # Создаем несколько целевых судов
    targets = [
        Vessel(
            id="target_1",
            position=Position(lat=44.6667, lon=33.5333),
            speed=10.0,
            course=180,
            vessel_type=VesselType.POWER_DRIVEN,
            name="Встречное судно"
        ),
        Vessel(
            id="target_2",
            position=Position(lat=44.6467, lon=33.5633),
            speed=8.0,
            course=270,
            vessel_type=VesselType.POWER_DRIVEN,
            name="Судно справа"
        ),
        Vessel(
            id="target_3",
            position=Position(lat=44.6367, lon=33.5533),
            speed=6.0,
            course=45,
            vessel_type=VesselType.SAILING,
            name="Парусное судно"
        ),
        Vessel(
            id="target_4",
            position=Position(lat=44.5967, lon=33.5733),
            speed=3.0,
            course=90,
            vessel_type=VesselType.FISHING,
            name="Рыболовное судно"
        )
    ]
    
    decision = decision_maker.make_decision(own_ship, targets)
    
    print(f"Ситуация: {decision.situation_summary}")
    print(f"Опасность столкновения: {'ДА' if decision.has_collision_risk else 'НЕТ'}")
    print()
    
    if decision.warnings:
        print("ПРЕДУПРЕЖДЕНИЯ:")
        for warning in decision.warnings:
            print(f"  ⚠️ {warning}")
        print()
    
    if decision.actions:
        print("РЕКОМЕНДОВАННЫЕ ДЕЙСТВИЯ:")
        for i, action in enumerate(decision.actions[:5], 1):  # Показываем первые 5
            print(f"  {i}. {action.description}")
            if action.sound_signal:
                print(f"     🔊 {action.sound_signal}")
            if action.light_signal:
                print(f"     💡 {action.light_signal}")
            print(f"     📋 Правило {action.rule_number}")
        print()


def test_priority_rules():
    """Тест приоритетов судов по МППСС-72"""
    print("=" * 60)
    print("ТЕСТ 4: Приоритеты судов по МППСС-72")
    print("=" * 60)
    
    vessels = [
        Vessel(id="power", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.POWER_DRIVEN),
        Vessel(id="sailing", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.SAILING),
        Vessel(id="fishing", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.FISHING),
        Vessel(id="nuc", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.NUC),
        Vessel(id="ram", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.RAM),
        Vessel(id="cbd", position=Position(0, 0), speed=0, course=0, vessel_type=VesselType.CBD),
    ]
    
    print("Приоритеты (от высшего к низшему):")
    sorted_vessels = sorted(vessels, key=lambda v: v.get_priority_level(), reverse=True)
    
    for i, v in enumerate(sorted_vessels, 1):
        priority_name = {
            VesselType.NUC: "NUC (лишенное возможности управляться)",
            VesselType.RAM: "RAM (ограниченное в возможности маневрировать)",
            VesselType.CBD: "CBD (стесненное осадкой)",
            VesselType.FISHING: "Fishing (занятое ловом рыбы)",
            VesselType.SAILING: "Sailing (парусное)",
            VesselType.POWER_DRIVEN: "Power-driven (с механическим двигателем)"
        }
        print(f"  {i}. {priority_name[v.vessel_type]} - уровень {v.get_priority_level()}")
    print()


if __name__ == "__main__":
    print("\n🚢 COLREG Decision System - Тестирование\n")
    
    test_tcpa_dcpa_calculation()
    test_encounter_classification()
    test_decision_making()
    test_priority_rules()
    
    print("=" * 60)
    print("✅ Все тесты завершены!")
    print("=" * 60)
    print("\nДля запуска веб-интерфейса выполните:")
    print("  python main.py")
    print("\nЗатем откройте браузер по адресу:")
    print("  http://localhost:8000")
    print()
