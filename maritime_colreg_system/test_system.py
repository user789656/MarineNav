"""
Главный файл запуска симуляции.
Запускает веб-сервер с визуализацией на географической карте.
"""

import os
import sys
import json
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, Any

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maritime_colreg_system.core import GeoPosition, calculate_tcpa_dcpa, calculate_bearing_and_range
from maritime_colreg_system.decision_maker import (
    COLREGDecisionMaker, 
    VesselType, 
    EncounterType,
    ManeuverType
)
from maritime_colreg_system.simulation import ScenarioGenerator, SimulatedVessel


class SimulationState:
    """Состояние симуляции."""
    
    def __init__(self):
        self.generator = ScenarioGenerator(seed=None)
        self.decision_maker = COLREGDecisionMaker(VesselType.POWER_DRIVEN)
        
        # Генерируем начальный сценарий
        self.own_vessel, self.targets = self.generator.generate_scenario(
            start_lat=44.95,
            start_lon=37.50,
            num_targets=6,
            create_risks=True
        )
        
        self.simulation_time = 0
        self.decisions_count = 0
        self.is_running = True
    
    def update(self, time_delta_minutes: float = 1.0):
        """Обновляет состояние симуляции."""
        self.simulation_time += time_delta_minutes
        
        # Обновляем позиции всех судов
        self.generator.update_scenario(self.own_vessel, self.targets, time_delta_minutes)
        
        # Принимаем решения для каждой цели
        for target in self.targets:
            decision = self.decision_maker.make_decision(
                own_pos=self.own_vessel.pos,
                own_speed=self.own_vessel.speed,
                own_course=self.own_vessel.course,
                target_pos=target.pos,
                target_speed=target.speed,
                target_course=target.course,
                target_type=target.vessel_type,
                target_id=target.id
            )
            
            # Применяем решение к нашему судну (если высокий риск)
            if decision.risk_level == "high" and decision.new_course is not None:
                # Плавно изменяем курс
                self.own_vessel.course = decision.new_course
                self.decisions_count += 1
            
            # Сохраняем решение в объекте цели для отображения
            target.current_decision = decision
        
        # Удаляем ушедшие суда и добавляем новые
        self.targets = self.generator.remove_passed_vessels(
            self.own_vessel, self.targets, max_distance_nm=15.0
        )
        self.targets = self.generator.spawn_new_vessels(
            self.own_vessel, self.targets, min_targets=4, max_targets=8
        )
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Возвращает состояние как словарь для JSON."""
        # Расчет параметров для каждой цели
        targets_data = []
        for target in self.targets:
            # TCPA/DCPA
            risk = calculate_tcpa_dcpa(
                self.own_vessel.pos, self.own_vessel.speed, self.own_vessel.course,
                target.pos, target.speed, target.course
            )
            
            # Пеленг и дистанция
            bearing, distance = calculate_bearing_and_range(self.own_vessel.pos, target.pos)
            
            # Решение
            decision = getattr(target, 'current_decision', None)
            
            target_data = {
                "id": target.id,
                "name": target.name,
                "lat": target.pos.lat,
                "lon": target.pos.lon,
                "speed": target.speed,
                "course": target.course,
                "vessel_type": target.vessel_type.value,
                "tcpa": risk.tcpa,
                "dcpa": risk.dcpa,
                "distance": distance,
                "bearing": bearing,
                "risk": decision.risk_level if decision else "low",
                "decision": decision.reasoning if decision else "",
                "signals": [
                    {
                        "pattern": s.pattern,
                        "description": s.description,
                        "type": s.signal_type
                    }
                    for s in decision.signals
                ] if decision and decision.signals else []
            }
            targets_data.append(target_data)
        
        return {
            "own_vessel": {
                "id": 0,
                "name": "НАШЕ СУДНО",
                "lat": self.own_vessel.pos.lat,
                "lon": self.own_vessel.pos.lon,
                "speed": self.own_vessel.speed,
                "course": self.own_vessel.course,
                "vessel_type": "POWER_DRIVEN"
            },
            "targets": targets_data,
            "simulation_time": self.simulation_time,
            "decisions_count": self.decisions_count,
            "is_running": self.is_running
        }


# Глобальное состояние симуляции
simulation_state = SimulationState()


class SimulationHandler(SimpleHTTPRequestHandler):
    """HTTP обработчик для симуляции."""
    
    def do_GET(self):
        """Обрабатывает GET запросы."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/simulation/state':
            # Возвращаем состояние симуляции
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            state = simulation_state.get_state_dict()
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode('utf-8'))
        
        elif parsed_path.path == '/':
            # Отдаем HTML файл
            self.path = '/web_frontend/index.html'
            return SimpleHTTPRequestHandler.do_GET(self)
        
        else:
            # Статические файлы
            return SimpleHTTPRequestHandler.do_GET(self)
    
    def log_message(self, format, *args):
        """Подавляет логирование."""
        pass


def simulation_loop():
    """Цикл обновления симуляции."""
    while simulation_state.is_running:
        try:
            simulation_state.update(time_delta_minutes=1.0)
            time.sleep(1.0)  # Обновление каждую секунду
        except Exception as e:
            print(f"Ошибка в цикле симуляции: {e}")
            time.sleep(1.0)


def main():
    """Точка входа приложения."""
    print("=" * 60)
    print("🚢 МППСС-72: Система Расхождения Судов")
    print("=" * 60)
    print()
    print("Запуск симуляции...")
    print()
    
    # Определяем порт
    port = int(os.environ.get('PORT', 8080))
    
    # Запускаем поток симуляции
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    
    # Запускаем HTTP сервер
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimulationHandler)
    
    print(f"✅ Сервер запущен!")
    print()
    print(f"📍 Откройте в браузере: http://localhost:{port}")
    print()
    print("🎮 Управление:")
    print("   - Нажмите 'Запуск' для начала симуляции")
    print("   - Наблюдайте за расхождением судов на карте")
    print("   - Следите за сигналами и решениями по МППСС-72")
    print()
    print("🛑 Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nОстановка симуляции...")
        simulation_state.is_running = False
        httpd.shutdown()
        print("Симуляция завершена.")


if __name__ == "__main__":
    main()
