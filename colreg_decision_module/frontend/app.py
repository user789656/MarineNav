"""
Flask web application for COLREG-72 Decision Module visualization.

This module provides a web interface to visualize vessel encounters,
collision risks, and recommended maneuvers with light/sound signals.
"""

from flask import Flask, render_template, jsonify, request
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from colreg_decision_module.models.vessel_model import (
    OwnVessel, TargetVessel, VesselType, VesselStatus
)
from colreg_decision_module.core.decision_engine import COLREGDecisionEngine
from colreg_decision_module.core.tcpa_calculator import TCPACalculator


app = Flask(__name__)


@app.route('/')
def index():
    """Render the main visualization page."""
    return render_template('index.html')


@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """Return list of available scenarios."""
    scenarios = {
        'headon': {
            'name': 'Head-On Situation',
            'rule': 'Rule 14',
            'description': 'Two power-driven vessels meeting on reciprocal courses'
        },
        'crossing': {
            'name': 'Crossing Situation',
            'rule': 'Rule 15',
            'description': 'Two power-driven vessels crossing paths'
        },
        'overtaking': {
            'name': 'Overtaking Situation',
            'rule': 'Rule 13',
            'description': 'One vessel overtaking another'
        },
        'multiple': {
            'name': 'Multiple Targets',
            'rule': 'Multiple Rules',
            'description': 'Complex scenario with multiple vessels'
        },
        'fishing': {
            'name': 'Fishing Vessel Encounter',
            'rule': 'Rule 18',
            'description': 'Encounter with a vessel engaged in fishing'
        }
    }
    return jsonify(scenarios)


@app.route('/api/decision', methods=['POST'])
def calculate_decision():
    """
    Calculate collision avoidance decision based on vessel data.
    
    Expected JSON payload:
    {
        "own_vessel": {
            "lat": 51.5,
            "lon": -0.1,
            "course": 0,
            "speed": 12,
            "vessel_type": "power_driven"
        },
        "target_vessels": [
            {
                "vessel_id": "TGT1",
                "lat": 51.55,
                "lon": -0.1,
                "course": 180,
                "speed": 12,
                "vessel_type": "power_driven"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'own_vessel' not in data:
            return jsonify({'error': 'Missing own_vessel data'}), 400
        
        # Create own vessel object
        own_data = data['own_vessel']
        own_vessel = OwnVessel(
            vessel_id=own_data.get('vessel_id', 'OWN'),
            lat=own_data['lat'],
            lon=own_data['lon'],
            course=own_data['course'],
            speed=own_data['speed'],
            vessel_type=VesselType(own_data.get('vessel_type', 'power_driven')),
            safety_domain=own_data.get('safety_domain', 1.0),
            min_safe_dcpa=own_data.get('min_safe_dcpa', 0.5)
        )
        
        # Create target vessel objects
        target_vessels = []
        for tgt_data in data.get('target_vessels', []):
            target = TargetVessel(
                vessel_id=tgt_data.get('vessel_id', f"TGT_{len(target_vessels)+1}"),
                lat=tgt_data['lat'],
                lon=tgt_data['lon'],
                course=tgt_data['course'],
                speed=tgt_data['speed'],
                vessel_type=VesselType(tgt_data.get('vessel_type', 'power_driven'))
            )
            target.update_relative_info(own_vessel.lat, own_vessel.lon, own_vessel.course)
            target_vessels.append(target)
        
        # Calculate decisions
        engine = COLREGDecisionEngine()
        decisions = engine.make_decisions(own_vessel, target_vessels)
        
        # Format response
        result = {
            'own_vessel': {
                'lat': own_vessel.lat,
                'lon': own_vessel.lon,
                'course': own_vessel.course,
                'speed': own_vessel.speed,
                'vessel_type': own_vessel.vessel_type.value
            },
            'targets': [],
            'decisions': []
        }
        
        # Add TCPA results for each target
        tcpa_calc = TCPACalculator()
        tcpa_results = tcpa_calc.calculate_all(own_vessel, target_vessels)
        
        for i, target in enumerate(target_vessels):
            tcpa_result = tcpa_results[i] if i < len(tcpa_results) else None
            target_dict = {
                'vessel_id': target.vessel_id,
                'lat': target.lat,
                'lon': target.lon,
                'course': target.course,
                'speed': target.speed,
                'vessel_type': target.vessel_type.value,
                'range_nm': round(target.range_nm, 3) if target.range_nm else None,
                'bearing_true': round(target.bearing_true, 1) if target.bearing_true else None,
                'relative_bearing': round(target.relative_bearing, 1) if target.relative_bearing else None
            }
            if tcpa_result:
                target_dict.update(tcpa_result.to_dict())
            result['targets'].append(target_dict)
        
        # Add decisions
        for decision in decisions:
            result['decisions'].append(decision.to_dict())
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/signals', methods=['GET'])
def get_signals_info():
    """Return information about COLREG signals."""
    from colreg_decision_module.core.signal_generator import SignalGenerator
    
    generator = SignalGenerator(vessel_length=20)
    
    signals_info = {
        'maneuver_signals': {
            'starboard': generator.get_maneuver_sound_signal('starboard').to_dict(),
            'port': generator.get_maneuver_sound_signal('port').to_dict(),
            'astern': generator.get_maneuver_sound_signal('astern').to_dict(),
            'doubt': generator.get_maneuver_sound_signal('doubt').to_dict()
        },
        'fog_signals': {
            'power_driven_making_way': generator.get_fog_signal(
                VesselType.POWER_DRIVEN, underway=True, making_way=True
            ).to_dict(),
            'power_driven_stopped': generator.get_fog_signal(
                VesselType.POWER_DRIVEN, underway=True, making_way=False
            ).to_dict()
        },
        'emergency': generator.get_emergency_signal() if hasattr(generator, 'get_emergency_signal') else {}
    }
    
    return jsonify(signals_info)


if __name__ == '__main__':
    print("🚢 Starting COLREG-72 Decision Module Web Interface...")
    print("📍 Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
