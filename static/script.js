// Forewarned - Dashboard JavaScript

let updateInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Forewarned Dashboard Initialized');
    refreshData();
    updateTime();
    
    // Auto-refresh every 30 seconds
    updateInterval = setInterval(refreshData, 30000);
    
    // Update time every second
    setInterval(updateTime, 1000);
});

async function refreshData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateWeatherAlerts(data.weather_alerts);
        updateEOCStates(data.eoc_states);
        updateEOCBanner(data.eoc_states);
        updateLocalAlertBanner(data.local_alert_state);
        updateLastUpdate(data.last_update);
        
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function updateWeatherAlerts(alerts) {
    const container = document.getElementById('weather-alerts');
    const countElement = document.getElementById('weather-count');
    const card = document.getElementById('weather-card');
    
    if (!container || !countElement || !card) {
        console.error('Missing weather alert elements:', { container, countElement, card });
        return;
    }
    
    countElement.textContent = alerts.length;
    
    // Update card color based on alert count
    if (alerts.length > 0) {
        card.classList.add('alert-active');
    } else {
        card.classList.remove('alert-active');
    }
    
    if (alerts.length === 0) {
        container.innerHTML = '<p class="no-data">No active alerts</p>';
        return;
    }
    
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${getSeverityClass(alert.severity)}">
            <div class="alert-header">
                <h3>${alert.event}</h3>
                <span class="severity-badge">${alert.severity}</span>
            </div>
            <p class="alert-headline">${alert.headline}</p>
            <p class="alert-areas"><strong>Areas:</strong> ${alert.areas}</p>
            <p class="alert-time"><strong>Expires:</strong> ${formatTime(alert.expires)}</p>
        </div>
    `).join('');
}

function updateLocalAlertBanner(alertState) {
    const banner = document.getElementById('local-alert-banner');
    const levelText = document.getElementById('local-alert-level');
    const detailDiv = document.getElementById('local-alert-detail');
    
    console.log('updateLocalAlertBanner called with:', alertState);
    
    if (!banner || !levelText || !alertState) {
        console.log('Missing elements or alertState:', { banner, levelText, alertState });
        return;
    }
    
    const level = alertState.level || 'none';
    console.log('Setting alert level to:', level);
    
    // Remove all level classes
    banner.className = 'alert-banner';
    
    // Add current level class
    const levelClass = `alert-banner-${level}`;
    banner.classList.add(levelClass);
    console.log('Applied class:', levelClass);
    
    // Update level text
    levelText.textContent = level.toUpperCase();
    
    // Update detail section
    if (detailDiv) {
        if (alertState.active && alertState.reason) {
            let detailText = alertState.reason;
            if (alertState.triggered_by && alertState.triggered_by.length > 0) {
                detailText += ` (${alertState.triggered_by.join(', ')})`;
            }
            detailDiv.textContent = detailText;
            console.log('Set detail text:', detailText);
        } else {
            detailDiv.textContent = '';
        }
    }
}

function updateEOCBanner(states) {
    const banner = document.getElementById('eoc-banner');
    const stateText = document.getElementById('eoc-banner-state');
    const detailDiv = document.getElementById('eoc-banner-detail');
    
    if (!banner || !stateText) return;
    
    const stateArray = Object.entries(states);
    
    // Find highest priority state
    const priorityStates = ['stand up', 'lean forward', 'alert', 'stand down', 'inactive'];
    let currentState = 'inactive';
    let activatedAreas = [];
    
    for (const priority of priorityStates) {
        const matchingStates = stateArray.filter(([_, s]) => s.state === priority);
        if (matchingStates.length > 0) {
            currentState = priority;
            activatedAreas = matchingStates.map(([area, _]) => area);
            break;
        }
    }
    
    // Remove all state classes
    banner.className = 'eoc-banner';
    
    // Add current state class
    const stateClass = `eoc-banner-${currentState.replace(/\s+/g, '-')}`;
    banner.classList.add(stateClass);
    
    // Update state text
    stateText.textContent = getEOCStateLabel(currentState).toUpperCase();
    
    // Update detail section
    if (detailDiv) {
        if (currentState !== 'inactive' && activatedAreas.length > 0) {
            detailDiv.textContent = activatedAreas.join(', ');
        } else {
            detailDiv.textContent = '';
        }
    }
}

function updateEOCStates(states) {
    const container = document.getElementById('eoc-states');
    const countElement = document.getElementById('eoc-count');
    const card = document.getElementById('eoc-card');
    
    if (!countElement || !card) {
        console.error('Missing EOC elements:', { container, countElement, card });
        return;
    }
    
    const stateArray = Object.entries(states);
    const activatedCount = stateArray.filter(([_, s]) => s.activated).length;
    
    // Find highest priority state
    const priorityStates = ['stand up', 'lean forward', 'alert', 'stand down', 'inactive'];
    let currentState = 'inactive';
    for (const priority of priorityStates) {
        if (stateArray.some(([_, s]) => s.state === priority)) {
            currentState = priority;
            break;
        }
    }
    
    // Update count with state label
    if (activatedCount > 0) {
        countElement.innerHTML = `<div class="eoc-state-label">${getEOCStateLabel(currentState)}</div>`;
    } else {
        countElement.textContent = activatedCount;
    }
    
    // Update card color based on activation
    if (activatedCount > 0) {
        card.classList.add('alert-active');
    } else {
        card.classList.remove('alert-active');
    }
    
    if (!container) return;
    
    if (stateArray.length === 0) {
        container.innerHTML = '<p class="no-data">No sites configured</p>';
        return;
    }
    
    container.innerHTML = stateArray.map(([url, state]) => `
        <div class="eoc-item ${state.activated ? 'activated' : 'monitoring'} eoc-${(state.state || 'inactive').replace(/\s+/g, '-')}">
            <div class="eoc-header">
                <h3>${getDomainName(url)}</h3>
                <span class="status-badge ${getEOCBadgeClass(state.state || 'inactive')}">
                    ${getEOCStateLabel(state.state || 'inactive')}
                </span>
            </div>
            <p class="eoc-url">${url}</p>
            <p class="eoc-time"><strong>Last Change:</strong> ${formatTime(state.last_change)}</p>
            ${state.state && state.state !== 'inactive' ? `<p class="eoc-state-desc">${getEOCStateDescription(state.state)}</p>` : ''}
        </div>
    `).join('');
}

function updateLastUpdate(timestamp) {
    const element = document.getElementById('last-update');
    if (!element) return;
    
    if (timestamp) {
        element.textContent = formatTime(timestamp);
    } else {
        element.textContent = 'Never';
    }
}

function getSeverityClass(severity) {
    const severityLower = (severity || '').toLowerCase();
    if (severityLower === 'extreme') return 'severity-extreme';
    if (severityLower === 'severe') return 'severity-severe';
    if (severityLower === 'moderate') return 'severity-moderate';
    return 'severity-minor';
}

function getDomainName(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch {
        return url;
    }
}

function getEOCStateLabel(state) {
    const labels = {
        'stand up': 'STAND UP',
        'lean forward': 'LEAN FORWARD',
        'alert': 'ALERT',
        'stand down': 'STAND DOWN',
        'inactive': 'INACTIVE'
    };
    return labels[state] || state.toUpperCase();
}

function getEOCBadgeClass(state) {
    if (state === 'stand up') return 'eoc-stand-up';
    if (state === 'lean forward') return 'eoc-lean-forward';
    if (state === 'alert') return 'eoc-alert';
    if (state === 'stand down') return 'eoc-stand-down';
    return 'inactive';
}

function getEOCStateDescription(state) {
    const descriptions = {
        'alert': 'Initial activation - monitoring situation',
        'lean forward': 'Preparing to activate operations',
        'stand up': 'LDMG fully activated and operational',
        'stand down': 'Deactivating and returning to normal'
    };
    return descriptions[state] || '';
}

function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch {
        return timestamp;
    }
}

function updateTime() {
    const now = new Date();
    
    // Format local time (HH:MM:SS)
    const localTime = now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    // Format UTC time (HH:MM:SS)
    const utcTime = now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'UTC'
    });
    
    // Format date (DD/MM/YYYY)
    const currentDate = now.toLocaleDateString('en-AU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
    
    // Format day of week
    const dayOfWeek = now.toLocaleDateString('en-US', {
        weekday: 'long'
    });
    
    // Update time displays
    const localElement = document.getElementById('local-time');
    const utcElement = document.getElementById('utc-time');
    
    if (localElement) {
        localElement.textContent = localTime;
    }
    
    if (utcElement) {
        utcElement.textContent = utcTime;
    }
    
    // Update date displays
    const dateElement = document.getElementById('current-date');
    const dayElement = document.getElementById('day-of-week');
    
    if (dateElement) {
        dateElement.textContent = currentDate;
    }
    
    if (dayElement) {
        dayElement.textContent = dayOfWeek;
    }
}
