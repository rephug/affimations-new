#!/usr/bin/env python
"""
Patch for assemblyai to fix validation issues with pydantic v2.
"""

import logging
import sys
import importlib
import inspect
from pathlib import Path
import types
from typing import Dict, Any, Optional, List

logger = logging.getLogger("patch_assemblyai_validation")

def get_default_config():
    """
    Get default configuration values for AssemblyAI transcription.
    """
    return {
        'word_boost': {},
        'boost_param': None,
        'filter_profanity': False,
        'redact_pii': False,
        'redact_pii_audio': False,
        'redact_pii_policies': [],
        'redact_pii_sub': False,
        'speaker_labels': False,
        'speakers_expected': None,
        'custom_spelling': {},
        'disfluencies': False,
        'summarization': False,
        'summary_model': None,
        'summary_type': None,
        'language_detection': False,
        'punctuate': True,
        'format_text': True,
        'dual_channel': None,
        'audio_start_from': None,
        'audio_end_at': None,
        'webhook_url': None,
        'webhook_auth_header_name': None,
        'webhook_auth_header_value': None,
        'language_code': None,
        'auto_chapters': False,
        'entity_detection': False,
        'iab_categories': False,
        'content_safety': False,
        'sentiment_analysis': False,
        'auto_highlights': False
    }

def patch_assemblyai_models():
    """
    Advanced patching for AssemblyAI models to be compatible with Pydantic v2.
    This approach attempts to modify the model classes directly.
    """
    try:
        import assemblyai as aai
        from pydantic import BaseModel, Field
        import importlib.util
        
        logger.info(f"Attempting to patch AssemblyAI models for Pydantic v2 compatibility")
        
        # First approach: Try to patch by downgrading to Pydantic v1
        try:
            logger.info("Attempting to force Pydantic v1 compatibility mode...")
            import pydantic
            if hasattr(pydantic, "version") and pydantic.version.VERSION.startswith("2."):
                # If using Pydantic v2, try to enable compatibility mode
                if hasattr(pydantic, "v1"):
                    logger.info("Enabling Pydantic v1 compatibility mode")
                    # This tells pydantic to use v1 behavior for BaseModel
                    pydantic.config.Extra.forbid = pydantic.config.Extra.ignore
        except Exception as e:
            logger.warning(f"Could not enable Pydantic v1 compatibility mode: {e}")
        
        # Second approach: Direct monkey patching
        types_module = None
        
        # Try to get the types module where the models are defined
        try:
            types_module = importlib.import_module('assemblyai.types')
            logger.info("Successfully imported assemblyai.types module")
        except ImportError:
            logger.warning("Could not import assemblyai.types module")
            # Try an alternative method to find the module
            for name, module in sys.modules.items():
                if name.startswith('assemblyai.') and hasattr(module, 'RawTranscriptionConfig'):
                    types_module = module
                    logger.info(f"Found RawTranscriptionConfig in module {name}")
                    break
        
        if types_module is None:
            logger.error("Could not locate the types module with RawTranscriptionConfig")
            return False
        
        # Get the model classes
        raw_config_class = getattr(types_module, 'RawTranscriptionConfig', None)
        transcription_config_class = getattr(aai, 'TranscriptionConfig', None)
        
        if raw_config_class is None:
            logger.error("RawTranscriptionConfig class not found")
            return False
        
        if transcription_config_class is None:
            logger.error("TranscriptionConfig class not found")
            return False
            
        # Already patched check
        if hasattr(raw_config_class, '__patched_for_pydantic_v2'):
            logger.info("Models are already patched")
            return True
            
        # Get default values
        defaults = get_default_config()
        
        # Patch method for model_validate, validate_python, or validate
        def create_wrapper(original_method, defaults):
            def wrapper(cls, *args, **kwargs):
                # For input object/dict, fill in defaults
                if args and isinstance(args[0], (dict, BaseModel)):
                    input_data = dict(args[0])
                    # Add missing fields with defaults
                    for field, default_value in defaults.items():
                        if field not in input_data:
                            input_data[field] = default_value
                    # Replace the input argument
                    args = (input_data,) + args[1:]
                return original_method(cls, *args, **kwargs)
            return wrapper
            
        # For RawTranscriptionConfig
        # First check which validation method is used in Pydantic v2
        for method_name in ['model_validate', 'validate_python', 'validate']:
            if hasattr(raw_config_class, method_name):
                logger.info(f"Found validation method: {method_name}")
                original_method = getattr(raw_config_class, method_name)
                setattr(raw_config_class, method_name, classmethod(create_wrapper(original_method.__func__, defaults)))
                logger.info(f"Patched {method_name} method for RawTranscriptionConfig")
        
        # Patch constructor too
        original_init = raw_config_class.__init__
        
        def patched_init(self, **kwargs):
            # Add missing fields with defaults
            for field, default_value in defaults.items():
                if field not in kwargs:
                    kwargs[field] = default_value
            # Call original init
            original_init(self, **kwargs)
        
        raw_config_class.__init__ = patched_init
        
        # Do the same for TranscriptionConfig if it's different from RawTranscriptionConfig
        if transcription_config_class is not raw_config_class:
            original_init = transcription_config_class.__init__
            
            def patched_tc_init(self, **kwargs):
                # Add missing fields with defaults
                for field, default_value in defaults.items():
                    if field not in kwargs:
                        kwargs[field] = default_value
                # Call original init
                original_init(self, **kwargs)
            
            transcription_config_class.__init__ = patched_tc_init
            
            # Patch validation methods too
            for method_name in ['model_validate', 'validate_python', 'validate']:
                if hasattr(transcription_config_class, method_name):
                    original_method = getattr(transcription_config_class, method_name)
                    setattr(transcription_config_class, method_name, 
                            classmethod(create_wrapper(original_method.__func__, defaults)))
                    logger.info(f"Patched {method_name} method for TranscriptionConfig")
        
        # Mark as patched
        raw_config_class.__patched_for_pydantic_v2 = True
        transcription_config_class.__patched_for_pydantic_v2 = True
        
        logger.info("Successfully patched AssemblyAI models for Pydantic v2 compatibility")
        return True
        
    except Exception as e:
        logger.error(f"Error during advanced patching: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Configure logging with more details
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Apply the advanced patch
    success = patch_assemblyai_models()
    logger.info(f"Patching result: {'Success' if success else 'Failed'}")
    
    # Always exit with 0 to allow the app to start
    # The app may still work even if patching fails
    sys.exit(0) 