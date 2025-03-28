# Morning Coffee Project - Cursor Cheatsheet

This cheatsheet provides quick reference commands and prompts for working with the Morning Coffee project in Cursor. Use these to boost your productivity!

## 🚀 Quick Commands

| Action | Cursor Command/Shortcut |
|--------|------------------------|
| Generate code | `/generate` or `Alt+G` |
| Edit code | `/edit` or `Alt+E` |
| Explain code | `/explain` or `Alt+X` |
| Chat about code | `/chat` or `Alt+C` |
| Generate docstring | `/docs` or select code + `/docs` |
| Generate tests | `/test` or select function + `/test` |
| Jump to definition | `Cmd/Ctrl + Click` |
| Quick file open | `Cmd/Ctrl + P` |
| Symbol search | `Cmd/Ctrl + T` |

## 🧩 Component-Specific Prompts

### Main Application

```
Generate a new Flask route for handling [specific] in app.py
```

```
Add Redis caching to the [specific] function in modules/[file].py
```

```
Refactor the error handling in modules/telnyx_handler.py
```

### Spark TTS Service

```
Optimize the TTS model loading in server.py
```

```
Add support for a new voice parameter in the Spark TTS API
```

```
Implement audio caching for frequently used phrases
```

### Docker Configuration

```
Add a volume for persistent data storage in docker-compose.yml
```

```
Configure environment-specific settings for development vs production
```

```
Optimize the Docker build process for faster builds
```

### Windmill Workflows

```
Create a new workflow for scheduling recurring calls
```

```
Add error handling to the transcription monitoring workflow
```

```
Optimize the job processing in the morning call workflow
```

## 🔧 Code Structure Templates

### New Module Template

```
/generate Create a new module for handling [feature] following the project structure
```

### API Handler Template

```
/generate Create an API handler for [service] with proper error handling and retries
```

### Flask Route Template

```
/generate Create a Flask route for [feature] with input validation and error responses
```

## 🔍 Troubleshooting Prompts

```
Debug why the TTS service might be failing to generate audio
```

```
Identify potential race conditions in the transcription monitoring
```

```
Check for memory leaks in the audio processing pipeline
```

## 🧪 Testing Prompts

```
Generate unit tests for the telnyx_handler.py module
```

```
Create integration tests for the TTS service API
```

```
Write a test case for handling network failures in API calls
```

## 📊 Performance Optimization

```
Optimize Redis usage for caching TTS responses
```

```
Reduce memory usage in the Spark TTS model loading
```

```
Implement batch processing for multiple transcription jobs
```

## 🔐 Security Review

```
Review the API key handling for security best practices
```

```
Check for potential injection vulnerabilities in user inputs
```

```
Improve secrets management in the Docker configuration
```

## 📚 Documentation Generation

```
Generate comprehensive API documentation for the main application endpoints
```

```
Create a sequence diagram for the call flow process
```

```
Document the environment variables used in the project
```

## 🛠️ Project-Specific Tasks

```
Add support for Telnyx messaging templates
```

```
Implement fall-back TTS when Spark TTS is unavailable
```

```
Create a health monitoring endpoint for all services
```

## ⚡ Patterns to Remember

For all API calls:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def api_call():
    # Your code here
```

For all environment variables:
```python
value = os.getenv('VARIABLE_NAME')
if not value:
    raise ValueError('VARIABLE_NAME environment variable is required')
```

For all Flask routes:
```python
@app.route('/endpoint', methods=['POST'])
def endpoint():
    try:
        data = request.json
        # Validate input
        if not data or 'required_field' not in data:
            return jsonify({"status": "error", "message": "Missing required field"}), 400
        
        # Process request
        # ...
        
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

Happy coding with Cursor!
