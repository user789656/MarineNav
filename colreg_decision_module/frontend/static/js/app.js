/**
 * COLREG-72 Decision Module - Frontend Application
 * 
 * This script handles the interactive visualization of vessel encounters,
 * displaying vessels on a map and showing collision risk assessments.
 */

// Global variables
let map;
let ownVesselMarker;
let targetMarkers = [];
let riskCircles = [];

// Default center (can be changed based on scenario)
const DEFAULT_CENTER = [51.5074, -0.1278]; // London area for demo

/**
 * Initialize the Leaflet map
 */
function initMap() {
    map = L.map('map').setView(DEFAULT_CENTER, 10);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
}

/**
 * Create vessel icon based on type
 */
function createVesselIcon(vesselType, isOwn = false) {
    const colors = {
        'power_driven': '#4299e1',
        'sailing': '#48bb78',
        'fishing': '#ed8936',
        'nuc': '#e53e3e',
        'ram': '#9f7aea',
        'cbd': '#ecc94b',
        'unknown': '#a0aec0'
    };
    
    const color = isOwn ? '#1a365d' : (colors[vesselType] || colors.unknown);
    const size = isOwn ? 20 : 12;
    
    return L.divIcon({
        className: 'vessel-marker',
        html: `<div style="
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [size, size],
        iconAnchor: [size/2, size/2]
    });
}

/**
 * Add own vessel to map
 */
function addOwnVessel(lat, lon, course) {
    if (ownVesselMarker) {
        map.removeLayer(ownVesselMarker);
    }
    
    ownVesselMarker = L.marker([lat, lon], {
        icon: createVesselIcon('power_driven', true)
    }).addTo(map);
    
    ownVesselMarker.bindPopup(`
        <strong>🚢 Own Vessel</strong><br>
        Position: ${lat.toFixed(4)}°, ${lon.toFixed(4)}°<br>
        Course: ${course}°
    `);
    
    // Add course indicator (arrow)
    const arrowLength = 0.01;
    const courseRad = (course - 90) * Math.PI / 180;
    const arrowEndLat = lat + arrowLength * Math.sin(courseRad);
    const arrowEndLon = lon + arrowLength * Math.cos(courseRad);
    
    L.polyline([[lat, lon], [arrowEndLat, arrowEndLon]], {
        color: '#1a365d',
        weight: 3,
        opacity: 0.8
    }).addTo(ownVesselMarker);
}

/**
 * Add target vessel to map
 */
function addTargetVessel(target) {
    const marker = L.marker([target.lat, target.lon], {
        icon: createVesselIcon(target.vessel_type)
    }).addTo(map);
    
    const riskColor = getRiskColor(target.collision_risk);
    
    marker.bindPopup(`
        <strong>⚓ Target: ${target.target_id}</strong><br>
        Type: ${target.vessel_type}<br>
        Position: ${target.lat.toFixed(4)}°, ${target.lon.toFixed(4)}°<br>
        Course: ${target.course}° | Speed: ${target.speed} kn<br>
        <hr>
        <strong>TCPA:</strong> ${target.tcpa_minutes} min<br>
        <strong>DCPA:</strong> ${target.dcpa_nm} NM<br>
        <strong>Range:</strong> ${target.range_nm} NM<br>
        <strong>Risk:</strong> <span style="color: ${riskColor}">${target.collision_risk.toUpperCase()}</span>
    `);
    
    targetMarkers.push(marker);
    
    // Add DCPA circle if there's risk
    if (target.collision_risk !== 'none') {
        const circle = L.circle([target.lat, target.lon], {
            radius: target.dcpa_nm * 1852, // Convert NM to meters
            color: riskColor,
            fillColor: riskColor,
            fillOpacity: 0.2
        }).addTo(map);
        riskCircles.push(circle);
    }
}

/**
 * Get color based on risk level
 */
function getRiskColor(risk) {
    const colors = {
        'high': '#e53e3e',
        'medium': '#dd6b20',
        'low': '#ecc94b',
        'none': '#48bb78'
    };
    return colors[risk] || colors.none;
}

/**
 * Clear all target markers
 */
function clearTargets() {
    targetMarkers.forEach(marker => map.removeLayer(marker));
    riskCircles.forEach(circle => map.removeLayer(circle));
    targetMarkers = [];
    riskCircles = [];
}

/**
 * Update situation overview panel
 */
function updateOverview(ownVessel, targets) {
    document.getElementById('own-speed').textContent = `${ownVessel.speed} kn`;
    document.getElementById('own-course').textContent = `${ownVessel.course}°`;
    document.getElementById('target-count').textContent = targets.length;
    
    const highRiskCount = targets.filter(t => t.collision_risk === 'high').length;
    document.getElementById('high-risk-count').textContent = highRiskCount;
}

/**
 * Update risk list panel
 */
function updateRiskList(targets) {
    const container = document.getElementById('risk-list');
    
    const risks = targets.filter(t => t.collision_risk !== 'none');
    
    if (risks.length === 0) {
        container.innerHTML = '<p class="no-data">No collision risks detected</p>';
        return;
    }
    
    container.innerHTML = risks.map(target => `
        <div class="risk-item ${target.collision_risk}">
            <h4>${target.target_id} - ${target.vessel_type}</h4>
            <p>TCPA: ${target.tcpa_minutes} min | DCPA: ${target.dcpa_nm} NM</p>
            <p>Range: ${target.range_nm} NM | Bearing: ${target.bearing_true}°</p>
        </div>
    `).join('');
}

/**
 * Update actions list panel
 */
function updateActionsList(decisions) {
    const container = document.getElementById('actions-list');
    
    const actions = decisions.filter(d => d.recommended_maneuver !== 'monitor_situation');
    
    if (actions.length === 0) {
        container.innerHTML = '<p class="no-data">No actions required - maintain course and speed</p>';
        return;
    }
    
    container.innerHTML = actions.map(decision => `
        <div class="action-item">
            <h4>${decision.target_id}: ${formatManeuver(decision.recommended_maneuver)}</h4>
            <p>${decision.reasoning}</p>
            ${decision.maneuver_angle ? `<p>Course change: ${decision.maneuver_angle}°</p>` : ''}
        </div>
    `).join('');
}

/**
 * Update signals list panel
 */
function updateSignalsList(decisions) {
    const container = document.getElementById('signals-list');
    
    let allSignals = [];
    decisions.forEach(decision => {
        if (decision.signals_required && decision.signals_required.length > 0) {
            allSignals = allSignals.concat(decision.signals_required.map(s => ({
                target: decision.target_id,
                signal: s
            })));
        }
    });
    
    if (allSignals.length === 0) {
        container.innerHTML = '<p class="no-data">No signals required</p>';
        return;
    }
    
    container.innerHTML = allSignals.map(item => `
        <div class="signal-item">
            <h4>${item.target}: ${formatSignal(item.signal)}</h4>
            <p>${getSignalMeaning(item.signal)}</p>
        </div>
    `).join('');
}

/**
 * Format maneuver name for display
 */
function formatManeuver(maneuver) {
    const names = {
        'alter_course_starboard': 'Alter Course to Starboard',
        'alter_course_port': 'Alter Course to Port',
        'reduce_speed': 'Reduce Speed',
        'stop_engines': 'Stop Engines',
        'reverse_engines': 'Reverse Engines',
        'maintain_course_speed': 'Maintain Course and Speed',
        'monitor_situation': 'Monitor Situation'
    };
    return names[maneuver] || maneuver;
}

/**
 * Format signal name for display
 */
function formatSignal(signal) {
    if (signal.includes('sound')) {
        const count = signal.includes('one') ? '1' : 
                     signal.includes('two') ? '2' : 
                     signal.includes('three') ? '3' : 
                     signal.includes('five') ? '5' : '?';
        return `🔊 ${count} blast(s)`;
    } else if (signal.includes('light')) {
        return '💡 Light signal';
    }
    return signal;
}

/**
 * Get human-readable signal meaning
 */
function getSignalMeaning(signal) {
    const meanings = {
        'sound_one_short_blast': 'I am altering my course to starboard',
        'sound_two_short_blasts': 'I am altering my course to port',
        'sound_three_short_blasts': 'I am operating astern propulsion',
        'sound_five_short_blasts': 'I doubt your intentions/actions',
        'light_one_flash_starboard': 'Starboard light signal',
        'light_two_flashes_port': 'Port light signal',
        'light_three_flashes_astern': 'Astern light signal'
    };
    return meanings[signal] || '';
}

/**
 * Load predefined scenario
 */
function loadScenario(scenarioName) {
    clearTargets();
    
    const scenarios = {
        'headon': getHeadOnScenario(),
        'crossing': getCrossingScenario(),
        'overtaking': getOvertakingScenario(),
        'multiple': getMultipleTargetsScenario(),
        'fishing': getFishingVesselScenario()
    };
    
    const scenario = scenarios[scenarioName];
    if (!scenario) return;
    
    // Add own vessel
    addOwnVessel(scenario.own.lat, scenario.own.lon, scenario.own.course);
    
    // Add targets
    scenario.targets.forEach(target => {
        addTargetVessel(target);
    });
    
    // Update panels
    updateOverview(scenario.own, scenario.targets);
    updateRiskList(scenario.targets);
    updateActionsList(scenario.decisions || []);
    updateSignalsList(scenario.decisions || []);
    
    // Fit map to show all vessels
    const bounds = L.latLngBounds([[scenario.own.lat, scenario.own.lon]]);
    scenario.targets.forEach(t => bounds.extend([t.lat, t.lon]));
    map.fitBounds(bounds, { padding: [50, 50] });
}

/**
 * Scenario: Head-On Situation (Rule 14)
 */
function getHeadOnScenario() {
    return {
        own: { lat: 51.5, lon: -0.1, course: 0, speed: 12 },
        targets: [{
            target_id: 'TGT1',
            vessel_type: 'power_driven',
            lat: 51.55, lon: -0.1, course: 180, speed: 12,
            tcpa_minutes: 15, dcpa_nm: 0.1, range_nm: 3.0,
            bearing_true: 0, collision_risk: 'high'
        }],
        decisions: [{
            target_id: 'TGT1',
            recommended_maneuver: 'alter_course_starboard',
            maneuver_angle: 45,
            reasoning: 'Head-on situation - alter course to starboard per Rule 14',
            signals_required: ['sound_one_short_blast', 'light_one_flash_starboard']
        }]
    };
}

/**
 * Scenario: Crossing Situation (Rule 15)
 */
function getCrossingScenario() {
    return {
        own: { lat: 51.5, lon: -0.1, course: 90, speed: 10 },
        targets: [{
            target_id: 'TGT1',
            vessel_type: 'power_driven',
            lat: 51.52, lon: -0.08, course: 0, speed: 10,
            tcpa_minutes: 12, dcpa_nm: 0.2, range_nm: 2.5,
            bearing_true: 45, collision_risk: 'high'
        }],
        decisions: [{
            target_id: 'TGT1',
            recommended_maneuver: 'alter_course_starboard',
            maneuver_angle: 60,
            reasoning: 'Crossing with vessel on starboard - alter to starboard to pass astern per Rule 15',
            signals_required: ['sound_one_short_blast', 'light_one_flash_starboard']
        }]
    };
}

/**
 * Scenario: Overtaking Situation (Rule 13)
 */
function getOvertakingScenario() {
    return {
        own: { lat: 51.5, lon: -0.1, course: 0, speed: 15 },
        targets: [{
            target_id: 'TGT1',
            vessel_type: 'power_driven',
            lat: 51.53, lon: -0.1, course: 0, speed: 8,
            tcpa_minutes: 20, dcpa_nm: 0.3, range_nm: 2.0,
            bearing_true: 0, collision_risk: 'medium'
        }],
        decisions: [{
            target_id: 'TGT1',
            recommended_maneuver: 'alter_course_starboard',
            maneuver_angle: 30,
            reasoning: 'Overtaking situation - keep clear of overtaken vessel per Rule 13',
            signals_required: ['sound_one_short_blast', 'light_one_flash_starboard']
        }]
    };
}

/**
 * Scenario: Multiple Targets
 */
function getMultipleTargetsScenario() {
    return {
        own: { lat: 51.5, lon: -0.1, course: 45, speed: 12 },
        targets: [
            {
                target_id: 'TGT1',
                vessel_type: 'power_driven',
                lat: 51.53, lon: -0.08, course: 225, speed: 10,
                tcpa_minutes: 18, dcpa_nm: 0.15, range_nm: 3.5,
                bearing_true: 35, collision_risk: 'high'
            },
            {
                target_id: 'TGT2',
                vessel_type: 'sailing',
                lat: 51.48, lon: -0.12, course: 90, speed: 6,
                tcpa_minutes: 25, dcpa_nm: 0.8, range_nm: 2.0,
                bearing_true: 220, collision_risk: 'low'
            },
            {
                target_id: 'TGT3',
                vessel_type: 'fishing',
                lat: 51.51, lon: -0.05, course: 180, speed: 3,
                tcpa_minutes: 30, dcpa_nm: 1.2, range_nm: 4.0,
                bearing_true: 85, collision_risk: 'none'
            }
        ],
        decisions: [
            {
                target_id: 'TGT1',
                recommended_maneuver: 'alter_course_starboard',
                maneuver_angle: 45,
                reasoning: 'Head-on situation - alter course to starboard per Rule 14',
                signals_required: ['sound_one_short_blast', 'light_one_flash_starboard']
            },
            {
                target_id: 'TGT2',
                recommended_maneuver: 'maintain_course_speed',
                maneuver_angle: null,
                reasoning: 'Sailing vessel on port side - we are stand-on per Rule 18',
                signals_required: []
            }
        ]
    };
}

/**
 * Scenario: Fishing Vessel Encounter
 */
function getFishingVesselScenario() {
    return {
        own: { lat: 51.5, lon: -0.1, course: 0, speed: 12 },
        targets: [{
            target_id: 'TGT1',
            vessel_type: 'fishing',
            lat: 51.54, lon: -0.1, course: 90, speed: 4,
            tcpa_minutes: 20, dcpa_nm: 0.3, range_nm: 3.0,
            bearing_true: 0, collision_risk: 'medium'
        }],
        decisions: [{
            target_id: 'TGT1',
            recommended_maneuver: 'alter_course_starboard',
            maneuver_angle: 45,
            reasoning: 'Fishing vessel has priority per Rule 18 - give way',
            signals_required: ['sound_one_short_blast', 'light_one_flash_starboard']
        }]
    };
}

/**
 * Initialize application on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    
    // Load default scenario
    loadScenario('headon');
    
    console.log('COLREG-72 Decision Module initialized');
});
