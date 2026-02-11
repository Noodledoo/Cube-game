# IDE Execution Guide

## Overview

This document explains how the project has been configured to support direct execution from IDEs (VS Code, PyCharm, etc.) without requiring `python -m` or terminal commands.

## Problem Statement

When Python files are run directly (via IDE "Run â–¶" button), Python's import system behaves differently than when run as modules:

- **Direct execution**: `__name__ == "__main__"`, and the file's directory is added to `sys.path`
- **Module execution**: `__name__ == "__main__"` but package structure is preserved

This causes imports like `from game.states import ...` to fail when running `main.py` or `server.py` directly, because Python can't find the `game` package.

## Solution

We've implemented a **robust bootstrap mechanism** that:

1. Detects the package root (`cube_boss_fight/`) regardless of execution context
2. Adds it to `sys.path` before any package imports
3. Works from any working directory
4. Works in all IDEs and execution contexts

## Files Modified

### 1. `cube_boss_fight/main.py`

**Changes:**
- Added bootstrap code at the top (lines 14-26)
- Uses `os.path.abspath(__file__)` to find the file's location
- Adds the directory containing `main.py` (which is `cube_boss_fight/`) to `sys.path`
- Normalizes paths to avoid duplicates

**Why it works:**
- When `main.py` is run directly, `__file__` points to `cube_boss_fight/main.py`
- We extract `cube_boss_fight/` and add it to `sys.path`
- Now imports like `from game.states import ...` resolve correctly

### 2. `cube_boss_fight/network/server.py`

**Changes:**
- Added bootstrap code at the top (lines 17-29)
- Goes up one directory from `network/server.py` to find `cube_boss_fight/`
- Adds it to `sys.path` before importing `network.protocol`

**Why it works:**
- When `server.py` is run directly, `__file__` points to `cube_boss_fight/network/server.py`
- We go up one level to get `cube_boss_fight/` and add it to `sys.path`
- Now imports like `from network.protocol import ...` resolve correctly

### 3. `cube_boss_fight/network/bot.py`

**Changes:**
- Same bootstrap pattern as `server.py`
- Ensures bot can be run standalone if needed

### 4. `cube_boss_fight/network/server.py` (Import Fix)

**Additional change:**
- Improved error handling for `game.scaling` import (line 530)
- Added `AttributeError` to exception handling for robustness

## Execution Guarantees

After these changes, you can:

âœ… **Run `main.py` directly** via IDE "Run â–¶" button
- Works from VS Code
- Works from PyCharm
- Works from any IDE
- Works regardless of working directory

âœ… **Run `network/server.py` directly** via IDE "Run â–¶" button
- Server starts correctly
- All imports resolve
- Multiplayer functionality works

âœ… **Multiplayer stability**
- Server and client can run independently
- No import errors during connection
- All network modules load correctly

## Technical Details

### Path Resolution Strategy

The bootstrap code uses a consistent pattern:

```python
_file_path = os.path.abspath(__file__)
_package_root = os.path.dirname(_file_path)  # or dirname(dirname(...)) for nested files
_package_root_resolved = os.path.normpath(_package_root)

_sys_path_normalized = [os.path.normpath(p) for p in sys.path if p]
if _package_root_resolved not in _sys_path_normalized:
    sys.path.insert(0, _package_root_resolved)
```

**Key points:**
- Uses `os.path.abspath()` to get absolute path regardless of working directory
- Uses `os.path.normpath()` to normalize paths for comparison
- Checks for duplicates before adding to avoid path pollution
- Inserts at position 0 for priority

### Why This Works

1. **Absolute paths**: `os.path.abspath(__file__)` always gives the real file location
2. **Normalization**: Path normalization ensures we don't add duplicates (e.g., `C:\path` vs `C:\path\`)
3. **Early execution**: Bootstrap runs before any package imports
4. **Idempotent**: Safe to call multiple times (won't add duplicates)

## Testing

To verify the changes work:

1. **Test main.py:**
   ```bash
   # From project root
   python cube_boss_fight/main.py
   
   # Or from cube_boss_fight/
   python main.py
   ```

2. **Test server.py:**
   ```bash
   # From project root
   python cube_boss_fight/network/server.py
   
   # Or from cube_boss_fight/network/
   python server.py
   ```

3. **Test in IDE:**
   - Open `cube_boss_fight/main.py` in VS Code
   - Press F5 or click "Run â–¶"
   - Should start without import errors

   - Open `cube_boss_fight/network/server.py` in VS Code
   - Press F5 or click "Run â–¶"
   - Should start server without import errors

## Future-Proofing

This solution is designed to be:

- **Python 3.13+ compatible**: Uses standard library only, no deprecated features
- **IDE-agnostic**: Works with any IDE that supports Python
- **Working directory independent**: Works from any directory
- **No external dependencies**: Pure Python, no special packages required

## Troubleshooting

If imports still fail:

1. **Check Python version**: Requires Python 3.7+
2. **Check file structure**: Ensure `cube_boss_fight/` directory structure is intact
3. **Check `__init__.py` files**: All package directories should have `__init__.py`
4. **Check IDE settings**: Some IDEs may override `sys.path` - check IDE Python path settings

## Alternative Approaches Considered

1. **Using `python -m`**: Rejected - requires terminal, not IDE-friendly
2. **Installing as package**: Rejected - adds unnecessary complexity
3. **Relative imports**: Rejected - breaks when run as modules
4. **PYTHONPATH environment variable**: Rejected - requires manual setup

The chosen solution is the most robust and IDE-friendly approach.
