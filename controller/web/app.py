"""
Web frontend for giri-prasad self-operating computer
"""
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import asyncio
import json
import time
from datetime import datetime
import sys
import os
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from operate.config import Config
from operate.models.apis import get_next_action
from operate.models.prompts import get_system_prompt, USER_QUESTION
from operate.utils.operating_system import OperatingSystem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'giri-prasad-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
config = Config()
operating_system = OperatingSystem()
session_logs = []
current_session = None
ollama_running = False


class ActionLogger:
    """Logger for tracking actions and rewards"""
    def __init__(self):
        self.actions = []
        self.total_reward = 0
        
    def log_action(self, action_type, details, success=None, reward=0):
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': action_type,
            'details': details,
            'success': success,
            'reward': reward
        }
        self.actions.append(log_entry)
        if success is not None:
            self.total_reward += reward
        return log_entry
    
    def get_summary(self):
        total = len(self.actions)
        successful = sum(1 for a in self.actions if a['success'] == True)
        failed = sum(1 for a in self.actions if a['success'] == False)
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'reward': self.total_reward,
            'success_rate': (successful / total * 100) if total > 0 else 0
        }


logger = ActionLogger()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/check-ollama', methods=['GET'])
def check_ollama():
    """Check if Ollama is running"""
    try:
        import ollama
        client = ollama.Client()
        # Try to list models to verify connection
        client.list()
        return jsonify({'running': True, 'message': 'Ollama is running'})
    except Exception as e:
        return jsonify({'running': False, 'message': str(e)}), 503


@app.route('/api/start-ollama', methods=['POST'])
def start_ollama():
    """Start Ollama server"""
    try:
        # Start Ollama serve in background
        if sys.platform == 'win32':
            subprocess.Popen(['ollama', 'serve'], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(['ollama', 'serve'])
        
        # Wait a bit for it to start
        time.sleep(2)
        
        return jsonify({'status': 'started', 'message': 'Ollama server started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
def start_session():
    """Start a new agent session"""
    data = request.json
    objective = data.get('objective', '')
    model = data.get('model', 'llava')
    
    if not objective:
        return jsonify({'error': 'Objective is required'}), 400
    
    # Check if Ollama is running first
    try:
        import ollama
        client = ollama.Client()
        client.list()
    except Exception as e:
        return jsonify({
            'error': 'Ollama is not running',
            'message': 'Please start Ollama server first or click "Start Ollama"',
            'details': str(e)
        }), 503
    
    # Create new session
    session_id = f"session_{int(time.time())}"
    
    # Log session start
    log_entry = logger.log_action('SESSION_START', {
        'objective': objective,
        'model': model
    }, success=None, reward=0)
    
    socketio.emit('log', log_entry)
    socketio.emit('session_started', {'session_id': session_id, 'objective': objective, 'model': model})
    
    # Start agent in background
    socketio.start_background_task(run_agent, objective, model, session_id)
    
    return jsonify({'session_id': session_id, 'status': 'started'})


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for an action"""
    data = request.json
    action_index = data.get('action_index')
    success = data.get('success')  # True/False
    
    if action_index is not None and action_index < len(logger.actions):
        action = logger.actions[action_index]
        
        # Calculate reward
        if success:
            reward = 10  # Positive reward
            action['success'] = True
        else:
            reward = -5  # Negative reward
            action['success'] = False
        
        action['reward'] = reward
        logger.total_reward += reward
        
        socketio.emit('feedback_received', {
            'action_index': action_index,
            'success': success,
            'reward': reward,
            'total_reward': logger.total_reward
        })
        
        return jsonify({'status': 'success', 'reward': reward})
    
    return jsonify({'error': 'Invalid action index'}), 400


@app.route('/api/logs')
def get_logs():
    """Get all logs"""
    return jsonify({
        'actions': logger.actions,
        'summary': logger.get_summary()
    })


@app.route('/api/stop', methods=['POST'])
def stop_session():
    """Stop current session"""
    global current_session
    current_session = None
    
    log_entry = logger.log_action('SESSION_STOP', {}, success=None, reward=0)
    socketio.emit('log', log_entry)
    socketio.emit('session_stopped', {})
    
    return jsonify({'status': 'stopped'})


def run_agent(objective, model, session_id):
    """Run the agent in background"""
    with app.app_context():
        try:
            # Initialize
            system_prompt = get_system_prompt(model, objective)
            system_message = {"role": "system", "content": system_prompt}
            messages = [system_message]
            
            loop_count = 0
            max_loops = 10
            
            while loop_count < max_loops:
                try:
                    # Log thinking
                    socketio.emit('agent_thinking', {
                        'loop': loop_count + 1,
                        'status': 'Analyzing screen...'
                    })
                    
                    # Get next action
                    operations, _ = asyncio.run(
                        get_next_action(model, messages, objective, session_id)
                    )
                    
                    # Log LLM response
                    llm_response_log = logger.log_action('LLM_RESPONSE', {
                        'operations': operations,
                        'loop': loop_count + 1
                    }, success=None, reward=0)
                    socketio.emit('log', llm_response_log)
                    socketio.emit('llm_response', {
                        'operations': operations,
                        'loop': loop_count + 1
                    })
                    
                    # Execute operations
                    for operation in operations:
                        time.sleep(1)
                        operate_type = operation.get("operation", "").lower()
                        operate_thought = operation.get("thought", "")
                        
                        if operate_type == "done":
                            summary = operation.get("summary", "")
                            log_entry = logger.log_action('DONE', {
                                'thought': operate_thought,
                                'summary': summary
                            }, success=True, reward=20)
                            socketio.emit('log', log_entry)
                            socketio.emit('objective_complete', {
                                'summary': summary,
                                'total_reward': logger.total_reward
                            })
                            return
                        
                        elif operate_type == "press":
                            keys = operation.get("keys", [])
                            operating_system.press(keys)
                            log_entry = logger.log_action('PRESS', {
                                'thought': operate_thought,
                                'keys': keys
                            }, success=None, reward=0)
                            socketio.emit('log', log_entry)
                            socketio.emit('action_executed', {
                                'type': 'press',
                                'details': keys,
                                'thought': operate_thought
                            })
                        
                        elif operate_type == "write":
                            content = operation.get("content", "")
                            operating_system.write(content)
                            log_entry = logger.log_action('WRITE', {
                                'thought': operate_thought,
                                'content': content
                            }, success=None, reward=0)
                            socketio.emit('log', log_entry)
                            socketio.emit('action_executed', {
                                'type': 'write',
                                'details': content,
                                'thought': operate_thought
                            })
                        
                        elif operate_type == "click":
                            # Legacy support
                            x = operation.get("x")
                            y = operation.get("y")
                            if x and y:
                                click_detail = {"x": x, "y": y}
                                operating_system.mouse(click_detail)
                                log_entry = logger.log_action('CLICK', {
                                    'thought': operate_thought,
                                    'x': x,
                                    'y': y
                                }, success=None, reward=0)
                                socketio.emit('log', log_entry)
                                socketio.emit('action_executed', {
                                    'type': 'click',
                                    'details': f"({x}, {y})",
                                    'thought': operate_thought
                                })
                    
                    loop_count += 1
                    
                except Exception as e:
                    error_log = logger.log_action('ERROR', {
                        'error': str(e),
                        'loop': loop_count
                    }, success=False, reward=-10)
                    socketio.emit('log', error_log)
                    socketio.emit('error', {'message': str(e)})
                    break
            
            # Max loops reached
            if loop_count >= max_loops:
                log_entry = logger.log_action('MAX_LOOPS', {
                    'loops': loop_count
                }, success=False, reward=-5)
                socketio.emit('log', log_entry)
                socketio.emit('session_ended', {'reason': 'Max loops reached'})
        
        except Exception as e:
            error_log = logger.log_action('FATAL_ERROR', {
                'error': str(e)
            }, success=False, reward=-20)
            socketio.emit('log', error_log)
            socketio.emit('error', {'message': f'Fatal error: {str(e)}'})


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
