# Giri-Prasad Web Interface

Modern web frontend for the AI-powered automation agent with real-time logging and reinforcement learning feedback.

## Features

✨ **Real-time Action Logging** - See every action the agent takes
🎯 **RL Feedback System** - Mark actions as success/failure with rewards
📊 **Live Statistics** - Track success rate, total reward, and performance
🧠 **LLM Response Viewer** - See raw model outputs
🎨 **Beautiful UI** - Modern, responsive design

## Installation

1. Install web dependencies:
```bash
pip install -r requirements-web.txt
```

## Running the Web Interface

1. Start the Flask server:
```bash
python -m controller.web.app
```

2. Open your browser to:
```
http://localhost:5000
```

## How to Use

### 1. Start a Session
- Enter your objective (e.g., "open notepad and type hello world")
- Select the AI model (llava, gemma3, mistral)
- Click "🚀 Start Agent"

### 2. Monitor Actions
- Watch real-time logs of every action
- See LLM responses with full operation details
- Track statistics: actions, success rate, total reward

### 3. Provide Feedback (RL Training)
- For each action, click:
  - **✓ Success** (+10 reward) - Action worked correctly
  - **✗ Failed** (-5 reward) - Action didn't work

### 4. View Results
- Total Reward: Cumulative RL score
- Success Rate: Percentage of successful actions
- Action Logs: Complete history with timestamps

## Reward System

| Action Result | Reward | Description |
|--------------|--------|-------------|
| Success ✓ | +10 | Action completed successfully |
| Failure ✗ | -5 | Action failed or incorrect |
| Objective Complete | +20 | Full objective achieved |
| Error | -10 | Exception or error occurred |
| Max Loops | -5 | Reached maximum iterations |

## API Endpoints

### POST /api/start
Start a new agent session
```json
{
  "objective": "open notepad",
  "model": "llava"
}
```

### POST /api/feedback
Submit feedback for an action
```json
{
  "action_index": 0,
  "success": true
}
```

### POST /api/stop
Stop the current session

### GET /api/logs
Get all logs and statistics

## Socket Events

### Client → Server
- None (uses HTTP API)

### Server → Client
- `session_started` - Session initialized
- `agent_thinking` - Agent analyzing screen
- `llm_response` - Raw LLM output
- `log` - New action logged
- `action_executed` - Action performed
- `feedback_received` - Feedback processed
- `objective_complete` - Task finished
- `session_stopped` - Session ended
- `error` - Error occurred

## Customization

### Change Port
Edit `app.py`:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

### Adjust Rewards
Edit reward values in `app.py`:
```python
if success:
    reward = 10  # Change positive reward
else:
    reward = -5  # Change negative reward
```

## Troubleshooting

**Can't connect to http://localhost:5000**
- Check if Flask server is running
- Try http://127.0.0.1:5000

**Actions not showing**
- Check browser console for errors
- Verify Socket.IO connection

**Ollama not responding**
- Make sure `ollama serve` is running
- Check model is pulled: `ollama pull llava`

## Architecture

```
Frontend (HTML/JS) → Socket.IO → Flask Server → Ollama API
                                       ↓
                              Action Logger (RL Tracking)
                                       ↓
                              Operating System Control
```

## Future Enhancements

- [ ] Save session history to database
- [ ] Export logs to JSON/CSV
- [ ] Model comparison view
- [ ] Screenshot preview in UI
- [ ] Voice command input
- [ ] Multi-session management
- [ ] RL model training integration
