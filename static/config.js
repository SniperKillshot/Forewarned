// Configuration page JavaScript
let currentConfig = {};
let ruleCounter = 0;

// Weather warning types (common Australian BOM types)
const weatherTypes = [
    'any',
    'Severe Thunderstorm Warning',
    'Severe Weather Warning',
    'Flood Warning',
    'Fire Weather Warning',
    'Tropical Cyclone Warning',
    'Tsunami Warning',
    'Heatwave Warning',
    'Damaging Winds',
    'Heavy Rainfall',
    'Large Hailstones',
    'Flash Flooding'
];

// Weather severity levels
const severityLevels = ['any', 'minor', 'moderate', 'severe', 'extreme'];

// LDMG states
const eocStates = ['alert', 'lean forward', 'stand up', 'stand down'];

// Load configuration on page load
document.addEventListener('DOMContentLoaded', () => {
    loadConfiguration();
    
    // Set up form submission
    document.getElementById('config-form').addEventListener('submit', saveConfiguration);
});

async function loadConfiguration() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        currentConfig = data;
        
        // Populate form with current configuration
        populateForm(data.alert_rules);
        
        showMessage('Configuration loaded', 'success');
    } catch (error) {
        console.error('Error loading configuration:', error);
        showMessage('Error loading configuration', 'error');
    }
}

function populateForm(alertRules) {
    // Clear existing rules
    ruleCounter = 0;
    
    ['advisory', 'watch', 'warning', 'emergency'].forEach(level => {
        const levelConfig = alertRules[level] || {};
        
        // Set operators
        const weatherOperator = levelConfig.weather_conditions?.operator || 'or';
        document.querySelector(`input[name="${level}_weather_operator"][value="${weatherOperator}"]`).checked = true;
        
        const eocOperator = levelConfig.eoc_conditions?.operator || 'or';
        document.querySelector(`input[name="${level}_eoc_operator"][value="${eocOperator}"]`).checked = true;
        
        // Set condition logic
        const conditionLogic = levelConfig.condition_logic || 'or';
        document.querySelector(`select[name="${level}_condition_logic"]`).value = conditionLogic;
        
        // Clear rule containers
        document.getElementById(`${level}-weather-rules`).innerHTML = '';
        document.getElementById(`${level}-eoc-rules`).innerHTML = '';
        
        // Add weather rules
        const weatherRules = levelConfig.weather_conditions?.rules || [];
        weatherRules.forEach(rule => {
            addWeatherRule(level, rule);
        });
        
        // Add EOC rules
        const eocRules = levelConfig.eoc_conditions?.rules || [];
        eocRules.forEach(rule => {
            addEOCRule(level, rule);
        });
    });
}

function addWeatherRule(level, ruleData = null) {
    const container = document.getElementById(`${level}-weather-rules`);
    const ruleId = `weather-rule-${ruleCounter++}`;
    
    const type = ruleData?.type || 'any';
    const severity = ruleData?.severity || 'any';
    
    const ruleDiv = document.createElement('div');
    ruleDiv.className = 'rule-item';
    ruleDiv.id = ruleId;
    ruleDiv.innerHTML = `
        <div class="rule-inputs">
            <label>
                Warning Type:
                <select class="rule-type" data-field="type">
                    ${weatherTypes.map(t => `<option value="${t}" ${t === type ? 'selected' : ''}>${t}</option>`).join('')}
                </select>
            </label>
            <label>
                Severity:
                <select class="rule-severity" data-field="severity">
                    ${severityLevels.map(s => `<option value="${s}" ${s === severity ? 'selected' : ''}>${s}</option>`).join('')}
                </select>
            </label>
        </div>
        <button type="button" class="remove-rule-btn" onclick="removeRule('${ruleId}')">✕ Remove</button>
    `;
    
    container.appendChild(ruleDiv);
}

function addEOCRule(level, ruleData = null) {
    const container = document.getElementById(`${level}-eoc-rules`);
    const ruleId = `eoc-rule-${ruleCounter++}`;
    
    const state = ruleData?.state || 'alert';
    
    const ruleDiv = document.createElement('div');
    ruleDiv.className = 'rule-item';
    ruleDiv.id = ruleId;
    ruleDiv.innerHTML = `
        <div class="rule-inputs">
            <label>
                LDMG State:
                <select class="rule-state" data-field="state">
                    ${eocStates.map(s => `<option value="${s}" ${s === state ? 'selected' : ''}>${s}</option>`).join('')}
                </select>
            </label>
        </div>
        <button type="button" class="remove-rule-btn" onclick="removeRule('${ruleId}')">✕ Remove</button>
    `;
    
    container.appendChild(ruleDiv);
}

function removeRule(ruleId) {
    const ruleElement = document.getElementById(ruleId);
    if (ruleElement) {
        ruleElement.remove();
    }
}

async function saveConfiguration(event) {
    event.preventDefault();
    
    console.log('Save configuration called');
    showMessage('Saving configuration...', 'success');
    
    try {
        // Build configuration object from form
        const alertRules = {};
        
        ['advisory', 'watch', 'warning', 'emergency'].forEach(level => {
            // Get weather operator
            const weatherOperator = document.querySelector(`input[name="${level}_weather_operator"]:checked`).value;
            
            // Get weather rules
            const weatherRules = [];
            document.querySelectorAll(`#${level}-weather-rules .rule-item`).forEach(ruleDiv => {
                const type = ruleDiv.querySelector('[data-field="type"]').value;
                const severity = ruleDiv.querySelector('[data-field="severity"]').value;
                weatherRules.push({ type, severity });
            });
            
            // Get EOC operator
            const eocOperator = document.querySelector(`input[name="${level}_eoc_operator"]:checked`).value;
            
            // Get EOC rules
            const eocRules = [];
            document.querySelectorAll(`#${level}-eoc-rules .rule-item`).forEach(ruleDiv => {
                const state = ruleDiv.querySelector('[data-field="state"]').value;
                eocRules.push({ state });
            });
            
            // Get condition logic
            const conditionLogic = document.querySelector(`select[name="${level}_condition_logic"]`).value;
            
            alertRules[level] = {
                weather_conditions: {
                    operator: weatherOperator,
                    rules: weatherRules
                },
                eoc_conditions: {
                    operator: eocOperator,
                    rules: eocRules
                },
                condition_logic: conditionLogic
            };
        });
        
        // Save to server
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ alert_rules: alertRules })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('Configuration saved successfully! Changes are active.', 'success');
        } else {
            showMessage(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showMessage('Error saving configuration', 'error');
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('status-message');
    messageDiv.textContent = message;
    messageDiv.className = `status-message ${type}`;
    messageDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}
