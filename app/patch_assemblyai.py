#!/usr/bin/env python
"""
Patch for assemblyai to work with pydantic v2.
This script should be run before importing assemblyai.
"""

import os
import logging
import sys
from importlib.util import find_spec
from pathlib import Path

logger = logging.getLogger("patch_assemblyai")

def patch_assemblyai():
    """
    Patch the assemblyai package to work with pydantic v2.
    
    In pydantic v2, BaseSettings has been moved to the pydantic_settings package.
    This patch modifies the assemblyai/types.py file to import BaseSettings
    from pydantic_settings instead of directly from pydantic.
    """
    try:
        # Find the assemblyai package location
        assemblyai_spec = find_spec('assemblyai')
        if not assemblyai_spec or not assemblyai_spec.origin:
            logger.error("Could not find assemblyai package")
            return False
        
        # Get the assemblyai package directory
        assemblyai_dir = Path(assemblyai_spec.origin).parent
        
        # Path to the types.py file which needs patching
        types_path = assemblyai_dir / 'types.py'
        
        if not types_path.exists():
            logger.error(f"Could not find {types_path}")
            return False
        
        # Read the current file content
        with open(types_path, 'r') as f:
            content = f.read()
        
        # Check if the file already imports from pydantic_settings
        if 'from pydantic_settings import BaseSettings' in content:
            logger.info("assemblyai/types.py is already patched")
            return True
        
        # Replace the import line
        new_content = content.replace(
            'from pydantic import BaseModel, BaseSettings, Extra',
            'from pydantic import BaseModel, Extra\nfrom pydantic_settings import BaseSettings'
        )
        
        # Write the patched file
        with open(types_path, 'w') as f:
            f.write(new_content)
        
        logger.info("Successfully patched assemblyai/types.py for pydantic v2 compatibility")
        return True
    
    except Exception as e:
        logger.error(f"Error patching assemblyai: {str(e)}")
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Apply the patch
    success = patch_assemblyai()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 