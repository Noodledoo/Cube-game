"""
Bootstrap utility for ensuring package imports work correctly
when files are run directly from an IDE or as scripts.

This module provides a robust way to ensure the package root
is in sys.path regardless of execution context.
"""

import os
import sys
from pathlib import Path


def _find_package_root():
    """
    Find the project root directory containing the cube_boss_fight package.
    
    This function works by:
    1. If __file__ is available (when imported), use it to locate the package
    2. Otherwise, search from current working directory upward
    3. Look for the cube_boss_fight directory
    
    Returns the absolute path to the project root (parent of cube_boss_fight/).
    """
    # Method 1: Use __file__ if we're being imported
    if '__file__' in globals():
        current_file = Path(__file__).resolve()
        # From core/bootstrap.py -> core/ -> cube_boss_fight/ -> project_root/
        package_root = current_file.parent.parent
        project_root = package_root.parent
        if (package_root / 'core' / 'bootstrap.py').exists():
            return str(project_root)
    
    # Method 2: Search from current working directory
    current = Path.cwd().resolve()
    while current != current.parent:
        cube_boss_fight_dir = current / 'cube_boss_fight'
        if cube_boss_fight_dir.is_dir() and (cube_boss_fight_dir / 'core' / 'bootstrap.py').exists():
            return str(current)
        current = current.parent
    
    # Method 3: Fallback - use directory containing cube_boss_fight if in sys.path
    for path_str in sys.path:
        if path_str:
            path = Path(path_str).resolve()
            cube_boss_fight_dir = path / 'cube_boss_fight'
            if cube_boss_fight_dir.is_dir():
                return str(path)
            # Also check if path itself is cube_boss_fight
            if path.name == 'cube_boss_fight' and (path / 'core' / 'bootstrap.py').exists():
                return str(path.parent)
    
    # Last resort: assume we're in the project root
    return str(Path.cwd().resolve())


def ensure_package_root_in_path():
    """
    Ensure the project root (containing cube_boss_fight/) is in sys.path.
    
    This function detects the project root and adds it to sys.path
    if it's not already there.
    
    Works correctly when:
    - Running files directly (python main.py, python network/server.py)
    - Running as modules (python -m cube_boss_fight.main)
    - Running from IDEs (VS Code, PyCharm, etc.)
    - Running from different working directories
    
    Safe to call multiple times - it won't add duplicates.
    
    Returns the project root path that was added/verified.
    """
    project_root = _find_package_root()
    project_root_path = Path(project_root).resolve()
    
    # Normalize to string for comparison
    project_root_str = str(project_root_path)
    
    # Add to sys.path if not already present
    # Check both the resolved path and the original string
    path_strings = [str(Path(p).resolve()) for p in sys.path if p]
    
    if project_root_str not in path_strings:
        sys.path.insert(0, project_root_str)
    
    return project_root_str


# Auto-execute when imported (but only if not already done)
if 'cube_boss_fight_bootstrap_done' not in sys.modules:
    ensure_package_root_in_path()
    sys.modules['cube_boss_fight_bootstrap_done'] = True
