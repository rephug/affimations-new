# Morning Coffee Project - Cursor Instructions

This document provides instructions and guidelines for working with the Morning Coffee project using Cursor IDE. These instructions are designed to help you navigate the codebase, understand the architecture, and use Cursor's AI capabilities effectively with this specific project.

## Project Setup in Cursor

1. **Open the Project**:
   - Open Cursor IDE
   - File > Open Folder > Select the morning-coffee project directory
   - Wait for the initial indexing to complete

2. **Configure Cursor**:
   - The project includes a `.cursorrules` file that configures Cursor's AI for this project
   - Cursor will automatically load these rules
   - You can verify this by checking the Cursor status bar (it should say "Morning Coffee Application")

3. **Install Extensions**:
   - Python (already included in Cursor)
   - Docker (for Docker and docker-compose support)
   - YAML (for better YAML editing)
   - Redis (for Redis configuration)

## Using AI Features with This Project

### Code Generation

When asking Cursor to generate code, use the following prompts for best results:

```
Create a Flask route for handling Telnyx webhook events.
```

```
Generate a Redis caching function for TTS responses.
```

```
Implement error handling for AssemblyAI API calls with retries.
```

### Code Understanding

To understand existing code, try these prompts:

```
Explain how the transcription monitoring workflow works.
```

```
How does the Spark TTS service generate and serve audio?
```

```
What is the call flow for the Telnyx integration?
```

### Code Modification

For modifying existing code:

```
Add logging to the LLM handler module.
```

```
Optimize the Docker configuration for production deployment.
```

```
Refactor the call state management to be more efficient.
```

## Project-Specific AI Prompts

For this project, structure your AI prompts by:

1. **Being specific about the component**:
   - "In the Spark TTS service..."
   - "For the Telnyx call handling..."
   - "In the Windmill workflow..."

2. **Mentioning relevant technologies**:
   - "...using Redis for caching..."
   - "...with AssemblyAI transcription..."
   - "...in the Docker development environment..."

3. **Specifying the context**:
   - "...for handling error cases..."
   - "...for optimizing performance..."
   - "...for adding new features..."

## Code Navigation Tips

Cursor provides powerful code navigation. Use these shortcuts to navigate the Morning Coffee codebase:

- **⌘+P** (or Ctrl+P): Quick file search
- **⌘+T** (or Ctrl+T): Symbol search
- **⌘+Shift+O** (or Ctrl+Shift+O): Navigate to symbols in the current file
- **⌘+Click** (or Ctrl+Click): Go to definition
- **⌘+Option+Left/Right** (or Alt+Left/Right): Navigate back/forward

## Effective Collaboration with Cursor AI

To work effectively with Cursor AI on this project:

1. **Start with the architecture**:
   ```
   What's the overall architecture of the Morning Coffee application?
   ```

2. **Understand a specific component**:
   ```
   Explain how the Telnyx integration works in the Morning Coffee app.
   ```

3. **Modify or extend a component**:
   ```
   How would I add support for a new TTS voice to the Spark TTS service?
   ```

4. **Debug issues**:
   ```
   What might cause the transcription monitoring to fail?
   ```

## Project Structure Guidance

When navigating the codebase, focus on these key areas:

- **`app/`**: Main Flask application
  - `app.py`: Entry point and API routes
  - `modules/`: Feature-specific modules

- **`spark-tts/`**: Spark TTS service
  - `server.py`: TTS API server
  - `download_model.py`: Model downloader

- **`windmill/`**: Workflow definitions
  - `workflows/`: Workflow YAML files

- **Docker Configuration**:
  - `docker-compose.yml`: Main configuration
  - `docker-compose.dev.yml`: Development overrides

## Using Cursor Terminal

For Docker operations, use the Cursor integrated terminal:

1. **Start development environment**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f
   ```

3. **Run tests**:
   ```bash
   docker-compose exec app pytest
   ```

## Advanced Cursor Features for This Project

1. **AI Code Review**:
   - Select code and ask "Review this code for potential issues"
   - Especially useful for API handling and error management

2. **Documentation Generation**:
   - Select a function and ask "Generate a docstring for this function"
   - Use for maintaining consistent documentation

3. **Refactoring Assistance**:
   - Select code and ask "Refactor this to follow the project's best practices"
   - Great for maintaining code quality

4. **Test Generation**:
   - Select code and ask "Generate unit tests for this function"
   - Helps maintain test coverage

## Troubleshooting Cursor with This Project

If you encounter issues:

1. **Cursor not recognizing project structure**:
   - Restart Cursor
   - Check that the `.cursorrules` file is properly formatted

2. **AI giving generic responses**:
   - Include specific project details in your prompt
   - Refer to specific files or components

3. **AI not respecting code style**:
   - Remind the AI of the project style in your prompt
   - Refer to specific examples in the codebase

Happy coding with Cursor and the Morning Coffee project!
