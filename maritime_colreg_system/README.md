# МППСС-72: Система Расхождения Судов

Система принятия решений для расхождения с судами по правилам МППСС-72 (COLREGs) с веб-визуализацией на географической карте.

## 📋 Описание

Проект реализует:
- **Модуль расчета TCPA/DCPA** - время и дистанция до точки ближайшего сближения
- **Модуль принятия решений COLREG** - определение типа ситуации и выбор маневра по правилам МППСС-72
- **Интеграцию с cv-core** - распознавание типов судов по изображению с камеры
- **Симулятор движения судов** - генерация реалистичных сценариев расхождения
- **Веб-визуализацию** - отображение судов на интерактивной карте Leaflet с сигналами и решениями

## 📁 Структура проекта

```
maritime-colreg-system/
├── core/                       # Базовые модули
│   ├── __init__.py
│   ├── geo.py                  # Геопространственные расчеты
│   └── collision.py            # Расчет TCPA/DCPA
├── decision_maker/             # Модуль принятия решений
│   ├── __init__.py
│   └── colreg_engine.py        # Движок правил МППСС-72
├── cv_integration/             # Интеграция с компьютерным зрением
│   ├── __init__.py
│   └── processor.py            # Обработка данных от CV-модуля
├── simulation/                 # Симуляция
│   ├── __init__.py
│   └── scenario.py             # Генератор сценариев
├── web_frontend/               # Веб-интерфейс
│   └── index.html              # Визуализация на карте
├── test_system.py              # Главный файл запуска
├── README.md                   # Этот файл
└── requirements.txt            # Зависимости
```

## 🚀 Быстрый старт

### Требования
- Python 3.8+
- Git Bash (для Windows)

### Установка и запуск

1. **Откройте Git Bash в папке проекта:**
```bash
cd /path/to/maritime-colreg-system
```

2. **Создайте виртуальное окружение (рекомендуется):**
```bash
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Запустите симуляцию:**
```bash
python test_system.py
```

5. **Откройте браузер:**
```
http://localhost:8080
```

6. **Нажмите "Запуск"** для начала симуляции

## 🎮 Управление

- **▶ Запуск** - начать симуляцию
- **⏸ Пауза** - приостановить симуляцию
- **🔄 Сброс** - перезапустить симуляцию

## 📊 Функционал

### Модуль принятия решений (COLREG)

Поддерживаемые правила МППСС-72:
- **Правило 13** - Обгон
- **Правило 14** - Встречный курс
- **Правило 15** - Пересечение курсов
- **Правило 17** - Действия стоящего на курсе судна

Типы судов:
- Судно с механическим двигателем (Power-driven)
- Парусное судно (Sailing)
- Судно, занятое ловом рыбы (Fishing)
- Судно, лишенное возможности управляться (NUC)
- Судно, ограниченное в возможности маневрировать (RAM)
- Судно, стесненное своей осадкой (CBD)

### Сигналы (Правило 34)

Автоматическая генерация звуковых и световых сигналов:
- **Один короткий** • - изменение курса вправо
- **Два коротких** •• - изменение курса влево
- **Три коротких** ••• - работа машиной заднего хода

### Визуализация

- **Географическая карта** Leaflet с OpenStreetMap
- **Маркеры судов** с цветовой индикацией риска
- **TCPA/DCPA** в реальном времени
- **Карточки судов** с полной информацией
- **Сигналы** в виде индикаторов

## 🔧 API

### GET /api/simulation/state

Возвращает текущее состояние симуляции:

```json
{
  "own_vessel": {
    "id": 0,
    "name": "НАШЕ СУДНО",
    "lat": 44.95,
    "lon": 37.50,
    "speed": 12.5,
    "course": 45.0,
    "vessel_type": "POWER_DRIVEN"
  },
  "targets": [...],
  "simulation_time": 120.5,
  "decisions_count": 15,
  "is_running": true
}
```

## 🧪 Тестирование

Для тестирования отдельных компонентов:

```python
from maritime_colreg_system.core import GeoPosition, calculate_tcpa_dcpa
from maritime_colreg_system.decision_maker import COLREGDecisionMaker, VesselType

# Создание позиций
own_pos = GeoPosition(lat=44.95, lon=37.50)
target_pos = GeoPosition(lat=44.96, lon=37.51)

# Расчет TCPA/DCPA
risk = calculate_tcpa_dcpa(
    own_pos, 12.0, 45.0,
    target_pos, 10.0, 225.0
)

print(f"TCPA: {risk.tcpa:.1f} мин, DCPA: {risk.dcpa:.0f} м")

# Принятие решения
dm = COLREGDecisionMaker()
decision = dm.make_decision(
    own_pos, 12.0, 45.0,
    target_pos, 10.0, 225.0,
    VesselType.POWER_DRIVEN,
    target_id=1
)

print(f"Маневр: {decision.maneuver.value}")
print(f"Сигналы: {[s.pattern for s in decision.signals]}")
```

## 🌐 Интеграция с cv-core

Для использования реального CV-модуля:

1. Убедитесь, что модели находятся в `cv-core-main/models/`
2. Используйте `CVProcessor` для обработки изображений:

```python
from maritime_colreg_system.cv_integration import CVProcessor

processor = CVProcessor(
    binary_model_path="cv-core-main/models/best_model.pth",
    shapes_model_path="cv-core-main/models/best.pt"
)

detections = processor.process_image("camera_frame.jpg")
```

## ⚙️ Конфигурация

Переменные окружения:
- `PORT` - порт веб-сервера (по умолчанию 8080)

## 📝 Лицензия

MIT License

## 👥 Авторы

Maritime AI Team
