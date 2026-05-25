/**
 * COLREG Decision System - Frontend JavaScript
 * Визуализация судов на карте и отображение рекомендаций
 */

// Глобальные переменные
let map = null;
let ownShipMarker = null;
let targetMarkers = {};
let trajectoryLines = {};
let dangerZoneCircle = null;

// Иконки для маркеров
const icons = {
    ownShip: L.divIcon({
        className: 'own-ship-icon',
        html: '<div style="font-size: 24px; color: #1a5f7a;">▲</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    }),
    targetShip: L.divIcon({
        className: 'target-ship-icon',
        html: '<div style="font-size: 20px; color: #dc3545;">●</div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    })
};

/**
 * Инициализация карты
 */
function initMap() {
    const defaultLat = 44.6167;
    const defaultLon = 33.5333;
    
    map = L.map('map').setView([defaultLat, defaultLon], 10);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
}

/**
 * Обновление позиции своего судна на карте
 */
function updateOwnShip(lat, lon, course) {
    if (ownShipMarker) {
        map.removeLayer(ownShipMarker);
    }
    
    // Поворот иконки по курсу
    const rotatedIcon = L.divIcon({
        className: 'own-ship-icon',
        html: `<div style="font-size: 24px; color: #1a5f7a; transform: rotate(${course}deg);">▲</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });
    
    ownShipMarker = L.marker([lat, lon], { icon: rotatedIcon })
        .addTo(map)
        .bindPopup('<b>Ваше судно</b><br>Курс: ' + course + '°');
    
    // Центрирование карты на своем судне
    map.setView([lat, lon], map.getZoom());
}

/**
 * Добавление целевого судна на карту
 */
function addTargetVessel(vessel) {
    const marker = L.marker([vessel.lat, vessel.lon], { icon: icons.targetShip })
        .addTo(map);
    
    const popupContent = `
        <b>${vessel.name || 'Судно ' + vessel.id}</b><br>
        Тип: ${getVesselTypeName(vessel.vessel_type)}<br>
        Курс: ${vessel.course}°<br>
        Скорость: ${vessel.speed} уз<br>
        Дистанция: ${vessel.distance?.toFixed(2) || '?'} миль<br>
        TCPA: ${vessel.tcpa?.toFixed(1) || '?'} мин<br>
        DCPA: ${vessel.dcpa?.toFixed(2) || '?'} миль<br>
        Риск: <span class="risk-badge ${vessel.risk_level || 'none'}">${getRiskLevelName(vessel.risk_level)}</span>
    `;
    
    marker.bindPopup(popupContent);
    targetMarkers[vessel.id] = marker;
    
    // Добавление траектории
    addTrajectoryLine(vessel);
}

/**
 * Добавление линии траектории движения судна
 */
function addTrajectoryLine(vessel) {
    if (trajectoryLines[vessel.id]) {
        map.removeLayer(trajectoryLines[vessel.id]);
    }
    
    // Расчет точки через 10 минут движения
    const distanceIn10Min = (vessel.speed / 60) * 10; // морские мили
    const endLat = vessel.lat + (distanceIn10Min * Math.cos(Math.radians(vessel.course))) / 60;
    const endLon = vessel.lon + (distanceIn10Min * Math.sin(Math.radians(vessel.course))) / 60;
    
    const line = L.polyline([
        [vessel.lat, vessel.lon],
        [endLat, endLon]
    ], {
        color: '#159895',
        weight: 2,
        dashArray: '5, 10',
        opacity: 0.7
    }).addTo(map);
    
    trajectoryLines[vessel.id] = line;
}

/**
 * Удаление всех целевых судов с карты
 */
function clearTargetVessels() {
    Object.values(targetMarkers).forEach(marker => map.removeLayer(marker));
    Object.values(trajectoryLines).forEach(line => map.removeLayer(line));
    targetMarkers = {};
    trajectoryLines = {};
}

/**
 * Отображение зоны опасности вокруг своего судна
 */
function showDangerZone(radius = 0.5) {
    if (dangerZoneCircle) {
        map.removeLayer(dangerZoneCircle);
    }
    
    if (!ownShipMarker) return;
    
    const position = ownShipMarker.getLatLng();
    
    dangerZoneCircle = L.circle(position, {
        radius: radius * 1852, // конверсия морских миль в метры
        color: '#ffc107',
        fillColor: '#ffc107',
        fillOpacity: 0.2,
        weight: 2,
        dashArray: '10, 10'
    }).addTo(map);
}

/**
 * Обновление панели с предупреждениями
 */
function updateWarnings(warnings) {
    const container = document.getElementById('warnings-container');
    container.innerHTML = '';
    
    if (!warnings || warnings.length === 0) {
        return;
    }
    
    warnings.forEach(warning => {
        const isCritical = warning.includes('КРИТИЧЕСКАЯ');
        const div = document.createElement('div');
        div.className = `warning-item ${isCritical ? 'critical' : ''}`;
        div.textContent = '⚠️ ' + warning;
        container.appendChild(div);
    });
}

/**
 * Обновление панели с рекомендованными действиями
 */
function updateActions(actions) {
    const container = document.getElementById('actions-container');
    container.innerHTML = '';
    
    if (!actions || actions.length === 0) {
        container.innerHTML = '<p>Нет рекомендованных действий</p>';
        return;
    }
    
    actions.forEach(action => {
        const card = document.createElement('div');
        card.className = `action-card priority-${action.priority}`;
        
        let signalsHtml = '';
        if (action.sound_signal) {
            signalsHtml += `<div class="signal">🔊 ${action.sound_signal}</div>`;
        }
        if (action.light_signal) {
            signalsHtml += `<div class="signal">💡 ${action.light_signal}</div>`;
        }
        
        card.innerHTML = `
            <h4>${getManeuverTypeName(action.maneuver_type)}</h4>
            <p>${action.description}</p>
            ${signalsHtml}
            <span class="rule-badge">Правило ${action.rule_number}</span>
        `;
        
        container.appendChild(card);
    });
}

/**
 * Обновление панели с сигналами
 */
function updateSignals(actions) {
    const container = document.getElementById('signals-container');
    container.innerHTML = '';
    
    const soundSignals = new Set();
    const lightSignals = new Set();
    
    actions?.forEach(action => {
        if (action.sound_signal) {
            soundSignals.add(action.sound_signal);
        }
        if (action.light_signal) {
            lightSignals.add(action.light_signal);
        }
    });
    
    if (soundSignals.size === 0 && lightSignals.size === 0) {
        container.innerHTML = '<p>Сигналы не требуются</p>';
        return;
    }
    
    soundSignals.forEach(signal => {
        const card = document.createElement('div');
        card.className = 'signal-card';
        card.innerHTML = `
            <span class="icon">🔊</span>
            <div class="details">
                <div class="description">${signal}</div>
                <div class="meaning">Звуковой сигнал</div>
            </div>
        `;
        container.appendChild(card);
    });
    
    lightSignals.forEach(signal => {
        const card = document.createElement('div');
        card.className = 'signal-card';
        card.innerHTML = `
            <span class="icon">💡</span>
            <div class="details">
                <div class="description">${signal}</div>
                <div class="meaning">Световой сигнал</div>
            </div>
        `;
        container.appendChild(card);
    });
}

/**
 * Обновление деталей по судам
 */
function updateVesselsDetails(vessels) {
    const container = document.getElementById('vessels-details');
    container.innerHTML = '';
    
    if (!vessels || vessels.length === 0) {
        container.innerHTML = '<p>Целевые суда отсутствуют</p>';
        return;
    }
    
    vessels.forEach(vessel => {
        const card = document.createElement('div');
        card.className = 'vessel-card';
        card.innerHTML = `
            <h4>${vessel.name || 'Судно ' + vessel.id}</h4>
            <div class="detail-row">
                <span>Тип:</span>
                <span>${getVesselTypeName(vessel.vessel_type)}</span>
            </div>
            <div class="detail-row">
                <span>Курс:</span>
                <span>${vessel.course}°</span>
            </div>
            <div class="detail-row">
                <span>Скорость:</span>
                <span>${vessel.speed} уз</span>
            </div>
            <div class="detail-row">
                <span>Дистанция:</span>
                <span>${vessel.distance?.toFixed(2) || '?'} миль</span>
            </div>
            <div class="detail-row">
                <span>Риск:</span>
                <span class="risk-badge ${vessel.risk_level || 'none'}">${getRiskLevelName(vessel.risk_level)}</span>
            </div>
        `;
        container.appendChild(card);
    });
}

/**
 * Вспомогательные функции для отображения названий
 */
function getVesselTypeName(type) {
    const names = {
        'power_driven': 'С мех. двигателем',
        'sailing': 'Парусное',
        'fishing': 'Рыболовное',
        'nuc': 'NUC (неуправляемое)',
        'ram': 'RAM (огранич. маневр.)',
        'cbd': 'CBD (стесн. осадкой)',
        'towing': 'Буксирующее',
        'seaplane': 'Гидросамолет'
    };
    return names[type] || type;
}

function getRiskLevelName(level) {
    const names = {
        'none': 'Нет',
        'low': 'Низкий',
        'medium': 'Средний',
        'high': 'Высокий',
        'critical': 'Критический'
    };
    return names[level] || level;
}

function getManeuverTypeName(type) {
    const names = {
        'keep_course': 'Сохранять курс',
        'turn_starboard': 'Поворот вправо',
        'turn_port': 'Поворот влево',
        'reduce_speed': 'Уменьшить скорость',
        'stop': 'Остановиться',
        'reverse': 'Задний ход',
        'increase_speed': 'Увеличить скорость'
    };
    return names[type] || type;
}

/**
 * Загрузка данных с сервера и обновление интерфейса
 */
async function updateSituation() {
    const ownShipData = {
        lat: parseFloat(document.getElementById('own-lat').value),
        lon: parseFloat(document.getElementById('own-lon').value),
        speed: parseFloat(document.getElementById('own-speed').value),
        course: parseFloat(document.getElementById('own-course').value),
        vessel_type: document.getElementById('vessel-type').value
    };
    
    const limitedVisibility = document.getElementById('limited-visibility').checked;
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                own_ship: ownShipData,
                limited_visibility: limitedVisibility
            })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка сервера');
        }
        
        const data = await response.json();
        
        // Обновление своего судна на карте
        updateOwnShip(ownShipData.lat, ownShipData.lon, ownShipData.course);
        
        // Очистка и добавление целевых судов
        clearTargetVessels();
        data.target_vessels?.forEach(vessel => {
            addTargetVessel(vessel);
        });
        
        // Показ зоны опасности если есть риск
        if (data.has_collision_risk) {
            showDangerZone(0.5);
        } else if (dangerZoneCircle) {
            map.removeLayer(dangerZoneCircle);
            dangerZoneCircle = null;
        }
        
        // Обновление панелей информации
        document.getElementById('situation-summary').innerHTML = `
            <p><strong>${data.situation_summary}</strong></p>
        `;
        
        updateWarnings(data.warnings);
        updateActions(data.actions);
        updateSignals(data.actions);
        updateVesselsDetails(data.target_vessels);
        
    } catch (error) {
        console.error('Ошибка обновления:', error);
        document.getElementById('situation-summary').innerHTML = `
            <p style="color: red;">Ошибка: ${error.message}</p>
        `;
    }
}

/**
 * Загрузка预设 сценариев
 */
async function loadScenario(scenarioType) {
    try {
        const response = await fetch(`/api/scenario/${scenarioType}`);
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки сценария');
        }
        
        const data = await response.json();
        
        // Заполнение формы данными своего судна
        document.getElementById('own-lat').value = data.own_ship.lat;
        document.getElementById('own-lon').value = data.own_ship.lon;
        document.getElementById('own-speed').value = data.own_ship.speed;
        document.getElementById('own-course').value = data.own_ship.course;
        document.getElementById('vessel-type').value = data.own_ship.vessel_type;
        
        // Обновление ситуации
        updateSituation();
        
    } catch (error) {
        console.error('Ошибка загрузки сценария:', error);
        alert('Ошибка загрузки сценария: ' + error.message);
    }
}

/**
 * Инициализация при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', () => {
    // Инициализация карты
    initMap();
    
    // Обработчики кнопок
    document.getElementById('btn-update').addEventListener('click', updateSituation);
    
    document.getElementById('btn-scenario-headon').addEventListener('click', () => {
        loadScenario('head_on');
    });
    
    document.getElementById('btn-scenario-crossing').addEventListener('click', () => {
        loadScenario('crossing');
    });
    
    document.getElementById('btn-scenario-overtaking').addEventListener('click', () => {
        loadScenario('overtaking');
    });
    
    // Первая загрузка с демо-данными
    updateSituation();
});
