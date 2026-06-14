# Plugin Guide (Beginner Friendly)

This guide explains plugins from zero to working example.

If you are new to Python, follow the steps exactly in order.

## What is a plugin?

A plugin is a small Python file in the `plugins/` folder.

When the app starts, it scans that folder and loads every `.py` file (except files that start with `_`).

Each plugin must provide a function named `register(context)`.

## Security first (important)

Plugins run as normal Python code on your computer.

That means a bad plugin can:

- read files
- modify or delete files
- run commands

Only install/import plugins from trusted sources.

## Folder and file rules

1. Put plugin files in `plugins/`
2. File extension must be `.py`
3. File must include `register(context)`
4. `register` must return a Python dictionary

## Minimum working plugin

Create a file `plugins/hello_plugin.py` with this exact content:

```python
def register(context: dict) -> dict:
    return {
        "id": "hello_plugin",
        "name": "Hello Plugin",
        "version": "1.0.0",
        "description": "My first working plugin.",
    }
```

Restart the app, then check plugin status in the Plugins page.

## What is inside context?

The app passes a dictionary named `context`:

- `project_root`: absolute path to the workspace root
- `plugins_dir`: absolute path to the plugins folder

Example:

```python
from pathlib import Path

def register(context: dict) -> dict:
    root = Path(context["project_root"])
    plugins = Path(context["plugins_dir"])

    return {
        "id": "context_demo",
        "name": "Context Demo",
        "version": "1.0.0",
        "description": f"Root: {root.name}, Plugins: {plugins.name}",
    }
```

## Return keys explained

You can return these keys:

- `id`: unique identifier for the plugin
- `name`: display name in UI/admin
- `version`: version label (for example `1.0.0`)
- `description`: short summary

If you skip a key, the app will use fallback defaults where possible.

## Step-by-step workflow for beginners

1. Create plugin file in `plugins/`
2. Paste minimum plugin template
3. Save file
4. Restart app
5. Open Plugins page
6. Verify plugin shows as loaded
7. If not loaded, check Troubleshooting section below

## Example: plugin with safe file config

```python
import json
from pathlib import Path

CONFIG_NAME = "my_safe_plugin_config.json"

def register(context: dict) -> dict:
    plugins_dir = Path(context["plugins_dir"])
    cfg_path = plugins_dir / CONFIG_NAME

    if not cfg_path.exists():
        cfg_path.write_text(
            json.dumps({"enabled": True, "mode": "normal"}, indent=2),
            encoding="utf-8",
        )

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    mode = data.get("mode", "normal")

    return {
        "id": "my_safe_plugin",
        "name": "My Safe Plugin",
        "version": "1.0.0",
        "description": f"Loaded with mode={mode}",
    }
```

## Example: robust plugin with error guard

```python
def register(context: dict) -> dict:
    try:
        # Put setup logic here
        return {
            "id": "guarded_plugin",
            "name": "Guarded Plugin",
            "version": "1.0.0",
            "description": "Loaded successfully.",
        }
    except Exception as exc:
        return {
            "id": "guarded_plugin",
            "name": "Guarded Plugin",
            "version": "1.0.0",
            "description": f"Recovered from error: {exc}",
        }
```

## Common mistakes and fixes

### Plugin not detected

- Check file is inside `plugins/`
- Check filename ends with `.py`
- Check file does not start with `_`

### Plugin detected but fails to load

- Ensure `register(context)` exists
- Ensure `register` returns a dict
- Remove syntax errors in Python code
- Remove imports of missing packages

### App starts but plugin behaves weird

- Keep `register` fast
- Avoid long loops/network calls in `register`
- Move heavy work into later app hooks (if added later)

## Best practices

1. Keep plugin code small and readable
2. Add clear `id`, `name`, and `description`
3. Handle missing files safely
4. Avoid side effects on import
5. Validate user/config input before use

## Plugin safety checklist before sharing

1. No hidden/obfuscated code
2. No hardcoded destructive file operations
3. No unexpected shell command execution
4. Clear version and description
5. Tested on fresh profile

## Quick copy template

```python
def register(context: dict) -> dict:
    return {
        "id": "my_plugin_id",
        "name": "My Plugin Name",
        "version": "1.0.0",
        "description": "What this plugin does.",
    }
```

---

If you are stuck, start from the minimum template again and add changes one small step at a time.
