# COLREG-72 Decision Module

A comprehensive Python module for maritime collision avoidance decision-making based on the International Regulations for Preventing Collisions at Sea (COLREG-72).

## Features

- **TCPA/DCPA Calculation**: Computes Time to Closest Point of Approach and Distance at CPA
- **Encounter Classification**: Identifies head-on, crossing, and overtaking situations
- **COLREG-72 Compliance**: Implements Rules 13-19 for vessel encounters
- **Decision Engine**: Provides maneuver recommendations with reasoning
- **Signal Generation**: Generates appropriate light and sound signals (Rules 34-35)
- **Web Visualization**: Interactive map-based interface for scenario visualization

## Project Structure

```
colreg-decision-module/
├── colreg_decision_module/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── tcpa_calculator.py      # TCPA/DCPA calculations
│   │   ├── encounter_classifier.py  # Encounter type classification
│   │   ├── decision_engine.py       # Main decision logic
│   │   └── signal_generator.py      # Light/sound signals
│   ├── models/
│   │   ├── __init__.py
│   │   └── vessel_model.py          # Vessel data classes
│   └── utils/
│       ├── __init__.py
│       └── geo_utils.py             # Geographic calculations
├── frontend/
│   ├── app.py                       # Flask web application
│   ├── templates/
│   │   └── index.html               # Main HTML template
│   └── static/
│       ├── css/style.css            # Styles
│       └── js/app.js                # Frontend JavaScript
├── examples/
│   └── demo.py                      # Usage examples
└── README.md
```

## Installation

```bash
# Install required dependencies
pip install flask

# Navigate to project directory
cd /workspace/colreg-decision-module
```

## Quick Start

### Run Demo Script

```bash
python examples/demo.py
```

This will demonstrate various encounter scenarios:
- Head-on situation (Rule 14)
- Crossing situation (Rule 15)
- Fishing vessel encounter (Rule 18)
- Multiple targets scenario

### Run Web Interface

```bash
python -m frontend.app
```

Then open http://localhost:5000 in your browser.

## Usage Examples

### Basic TCPA Calculation

```python
from colreg_decision_module.models.vessel_model import OwnVessel, TargetVessel, VesselType
from colreg_decision_module.core.tcpa_calculator import TCPACalculator

# Create vessels
own = OwnVessel(lat=51.5, lon=-0.1, course=0, speed=12, vessel_type=VesselType.POWER_DRIVEN)
target = TargetVessel(lat=51.55, lon=-0.1, course=180, speed=12, vessel_type=VesselType.POWER_DRIVEN)

# Calculate TCPA
calculator = TCPACalculator()
result = calculator.calculate_single(own, target)

print(f"TCPA: {result.tcpa_minutes} min")
print(f"DCPA: {result.dcpa_nm} NM")
print(f"Risk: {result.collision_risk}")
```

### Full Decision Making

```python
from colreg_decision_module.core.decision_engine import COLREGDecisionEngine

engine = COLREGDecisionEngine()
decisions = engine.make_decisions(own, [target])

for decision in decisions:
    print(f"Target: {decision.target_id}")
    print(f"Maneuver: {decision.recommended_maneuver.value}")
    print(f"Signals: {decision.signals_required}")
    print(f"Reasoning: {decision.reasoning}")
```

### Signal Generation

```python
from colreg_decision_module.core.signal_generator import SignalGenerator
from colreg_decision_module.models.vessel_model import VesselType, VesselStatus

generator = SignalGenerator(vessel_length=25)

# Get navigation lights
lights = generator.get_lights_for_vessel(VesselType.POWER_DRIVEN, VesselStatus.UNDERWAY)

# Get maneuver sound signal
signal = generator.get_maneuver_sound_signal('starboard')
print(f"Signal: {signal.count} short blast(s)")
```

## COLREG-72 Rules Implemented

### Part B - Steering and Sailing Rules

| Rule | Description | Implementation |
|------|-------------|----------------|
| 13 | Overtaking | `EncounterClassifier._apply_encounter_rules()` |
| 14 | Head-on Situation | `COLREGDecisionEngine._give_way_action()` |
| 15 | Crossing Situation | `COLREGDecisionEngine._give_way_action()` |
| 16 | Action by Give-way Vessel | Decision urgency levels |
| 17 | Action by Stand-on Vessel | `COLREGDecisionEngine._stand_on_action()` |
| 18 | Responsibilities Between Vessels | `EncounterClassifier._determine_responsibility()` |
| 19 | Restricted Visibility | Fog signal generation |

### Part C - Lights and Shapes

| Rule | Description | Implementation |
|------|-------------|----------------|
| 23 | Power-driven Vessels | `SignalGenerator._get_power_driven_lights()` |
| 25 | Sailing Vessels | `SignalGenerator._get_sailing_lights()` |
| 26 | Fishing Vessels | `SignalGenerator._get_fishing_lights()` |
| 27 | NUC/RAM Vessels | `SignalGenerator._get_nuc_lights()`, `_get_ram_lights()` |
| 28 | Constrained by Draft | `SignalGenerator._get_cbd_lights()` |

### Part D - Sound and Light Signals

| Rule | Description | Implementation |
|------|-------------|----------------|
| 34 | Maneuvering Signals | `SignalGenerator.get_maneuver_sound_signal()` |
| 35 | Fog Signals | `SignalGenerator.get_fog_signal()` |

## API Reference

### Core Classes

#### `TCPACalculator`
- `calculate_single(own_vessel, target_vessel)` - Calculate TCPA for one target
- `calculate_all(own_vessel, target_vessels)` - Calculate for multiple targets
- `get_high_risk_targets(own_vessel, target_vessels)` - Filter high-risk targets

#### `EncounterClassifier`
- `classify(own_vessel, target_vessel, relative_bearing)` - Classify encounter type
- `get_relative_bearing_sector(relative_bearing)` - Get bearing sector name

#### `COLREGDecisionEngine`
- `make_decisions(own_vessel, target_vessels)` - Generate all decisions
- `get_emergency_signal()` - Get distress signal information

#### `SignalGenerator`
- `get_lights_for_vessel(vessel_type, status)` - Get navigation lights
- `get_maneuver_sound_signal(maneuver_type)` - Get maneuver sound signal
- `get_day_shapes_for_vessel(vessel_type, status)` - Get day shapes
- `get_fog_signal(vessel_type, underway, making_way)` - Get fog signal

### Data Models

#### `OwnVessel`
```python
OwnVessel(
    lat: float,           # Latitude in degrees
    lon: float,           # Longitude in degrees
    course: float,        # Course in degrees (0-360)
    speed: float,         # Speed in knots
    vessel_type: VesselType,
    safety_domain: float = 1.0,      # NM
    min_safe_dcpa: float = 0.5,      # NM
    max_tcpa_threshold: float = 20.0 # minutes
)
```

#### `TargetVessel`
```python
TargetVessel(
    vessel_id: str,
    lat: float,
    lon: float,
    course: float,
    speed: float,
    vessel_type: VesselType,
    confidence: float = 1.0  # Detection confidence from CV
)
```

## Vessel Types

The module supports the following vessel types according to COLREG-72:

- `POWER_DRIVEN` - Vessel propelled by machinery
- `SAILING` - Vessel under sail
- `FISHING` - Vessel engaged in fishing
- `NUC` - Not Under Command
- `RAM` - Restricted Ability to Maneuver
- `CBD` - Constrained By Draft
- `SEAPLANE` - Aircraft on water

## License

MIT License

## Author

Maritime AI Team

## Contributing

Contributions are welcome! Please ensure code follows the existing style and includes appropriate tests.
