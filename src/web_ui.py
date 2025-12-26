"""Flask web UI for Forewarned"""
import logging
import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime

logger = logging.getLogger(__name__)

# Global state (will be updated by monitors)
app_state = {
    'weather_alerts': [],
    'eoc_states': {},
    'last_update': None,
    'local_alert_state': {
        'active': False,
        'level': 'none',  # none, advisory, watch, warning, emergency
        'reason': '',
        'timestamp': None,
        'triggered_by': []  # List of alert types or EOC states that triggered this
    }
}


def create_app():
    """Create and configure Flask application"""
    # Get the base directory (parent of src folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Disable template caching for development
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    # Store VOIP integration reference
    app.voip_integration = None
    
    @app.route('/')
    def index():
        """Main dashboard"""
        return render_template('index.html')
    
    @app.route('/api/status')
    def api_status():
        """Get current status"""
        return jsonify({
            'weather_alerts': app_state['weather_alerts'],
            'eoc_states': app_state['eoc_states'],
            'local_alert_state': app_state['local_alert_state'],
            'last_update': app_state['last_update']
        })
    
    @app.route('/api/weather')
    def api_weather():
        """Get weather alerts"""
        return jsonify({
            'alerts': app_state['weather_alerts'],
            'count': len(app_state['weather_alerts'])
        })
    
    @app.route('/api/eoc')
    def api_eoc():
        """Get EOC states"""
        return jsonify({
            'states': app_state['eoc_states'],
            'activated_count': sum(1 for s in app_state['eoc_states'].values() if s.get('activated', False))
        })
    
    @app.route('/api/local_alert')
    def api_local_alert():
        """Get local alert state"""
        return jsonify(app_state['local_alert_state'])
    
    @app.route('/config')
    def config_page():
        """Configuration page"""
        return render_template('config.html')
    
    @app.route('/api/config', methods=['GET'])
    def api_get_config():
        """Get current configuration"""
        from .config import load_config
        config = load_config()
        return jsonify({
            'alert_rules': config.get('alert_rules', {}),
            'alert_types': config.get('alert_types', [])
        })
    
    @app.route('/api/config', methods=['POST'])
    def api_save_config():
        """Save configuration"""
        try:
            from .config import load_config, save_config
            
            # Get current config
            config = load_config()
            
            # Get new alert rules from request
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Update alert rules
            if 'alert_rules' in data:
                config['alert_rules'] = data['alert_rules']
            
            # Save config
            save_config(config)
            
            # Reload config in alert manager if available
            if 'alert_manager' in app_state:
                app_state['alert_manager'].config = config
                logger.info("Alert manager config reloaded")
            
            return jsonify({'success': True, 'message': 'Configuration saved'})
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    
    # ========== VOIP Endpoints ==========
    
    @app.route('/voip/status', methods=['GET', 'POST'])
    def voip_status():
        """VOIP status endpoint - returns JSON with current alert state"""
        from flask import Response
        
        state = app_state['local_alert_state']
        
        # Generate TTS message
        if not state.get('active'):
            message = "There are currently no active alerts. All systems normal."
        else:
            level = state.get('level', 'unknown')
            reason = state.get('reason', 'Unknown reason')
            level_name = level.upper()
            
            message = f"Current alert level is {level_name}. {reason}. "
            
            if level == 'emergency':
                message += "This is an emergency. Take immediate action."
            elif level == 'warning':
                message += "This is a warning. Take appropriate precautions."
            elif level == 'watch':
                message += "This is a watch alert. Monitor conditions closely."
            elif level == 'advisory':
                message += "This is an advisory. Be aware of conditions."
        
        return jsonify({
            'active': state.get('active', False),
            'level': state.get('level', 'none'),
            'reason': state.get('reason', ''),
            'message': message
        })
    
    @app.route('/voip/twiml', methods=['GET', 'POST'])
    def voip_twiml():
        """TwiML endpoint for Twilio VOIP integration"""
        from flask import Response
        
        state = app_state['local_alert_state']
        
        # Generate message
        if not state.get('active'):
            message = "There are currently no active alerts. All systems normal."
        else:
            level = state.get('level', 'unknown')
            reason = state.get('reason', 'Unknown reason')
            message = f"Current alert level is {level.upper()}. {reason}."
        
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{message}</Say>
    <Pause length="2"/>
    <Say voice="alice">Press 1 to repeat this message. Press 2 to hang up.</Say>
    <Gather numDigits="1" action="/voip/menu" method="POST">
        <Pause length="5"/>
    </Gather>
    <Say voice="alice">Goodbye.</Say>
</Response>'''
        
        return Response(twiml, mimetype='text/xml')
    
    @app.route('/voip/menu', methods=['POST'])
    def voip_menu():
        """Handle TwiML menu selections"""
        from flask import Response
        
        digit = request.form.get('Digits', '')
        
        if digit == '1':
            # Repeat - redirect back to status
            return voip_twiml()
        else:
            # Hang up
            twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Goodbye.</Say>
    <Hangup/>
</Response>'''
            return Response(twiml, mimetype='text/xml')
    
    @app.route('/voip/agi', methods=['GET'])
    def voip_agi():
        """Asterisk AGI script endpoint"""
        from flask import Response
        
        state = app_state['local_alert_state']
        
        # Generate message
        if not state.get('active'):
            message = "There are currently no active alerts. All systems normal."
        else:
            level = state.get('level', 'unknown')
            reason = state.get('reason', 'Unknown reason')
            message = f"Current alert level is {level.upper()}. {reason}."
        
        # AGI script format
        agi_script = f'''ANSWER
WAIT 1
EXEC Set(CHANNEL(language)=en)
EXEC SayText("{message}")
WAIT 2
HANGUP
'''
        
        return Response(agi_script, mimetype='text/plain')
    
    @app.route('/api/voip/test-call', methods=['POST'])
    def voip_test_call():
        """Test VOIP call endpoint"""
        if not app.voip_integration:
            return jsonify({'error': 'VOIP integration not configured'}), 400
        
        data = request.get_json()
        extension = data.get('extension')
        alert_level = data.get('alert_level', 'warning')
        reason = data.get('reason', 'Test call')
        
        if not extension:
            return jsonify({'error': 'extension required'}), 400
        
        # Make the call asynchronously
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(
            app.voip_integration.make_alert_call(extension, alert_level, reason)
        )
        
        if success:
            return jsonify({'success': True, 'message': f'Call initiated to {extension}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to initiate call'}), 500
    
    # ========== End VOIP Endpoints ==========
    
    return app


def update_state(weather_alerts=None, eoc_states=None, local_alert_state=None):
    """
    Update global application state
    
    Args:
        weather_alerts: List of active weather alerts
        eoc_states: Dictionary of EOC states
        local_alert_state: Local alert state dictionary
    """
    if weather_alerts is not None:
        app_state['weather_alerts'] = weather_alerts
    if eoc_states is not None:
        app_state['eoc_states'] = eoc_states
    if local_alert_state is not None:
        app_state['local_alert_state'] = local_alert_state
    app_state['last_update'] = datetime.now().isoformat()


def update_local_alert_state(active: bool, level: str = 'none', reason: str = '', triggered_by: list = None):
    """
    Update the local alert state - this is what triggers Home Assistant routines
    
    Args:
        active: Whether alert is active
        level: Alert level (none, advisory, watch, warning, emergency)
        reason: Human-readable reason for the alert
        triggered_by: List of triggers (weather alerts, EOC states, etc.)
    """
    app_state['local_alert_state'] = {
        'active': active,
        'level': level,
        'reason': reason,
        'timestamp': datetime.now().isoformat(),
        'triggered_by': triggered_by or []
    }
    logger.info(f"Local alert state updated: active={active}, level={level}, reason={reason}")
    return app_state['local_alert_state']
