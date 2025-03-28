#!/usr/bin/env python
# OpenAI Voice Style Example for Morning Coffee TTS

import os
import argparse
import sys
import time
import wave
import pyaudio
from typing import Optional

# Add parent directory to path to import modules from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.tts.tts_service import TTSService
from modules.tts.provider_factory import TTSProviderFactory

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test OpenAI TTS with voice styles")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--text", default="Hello! I'm a text-to-speech system using OpenAI's new voice models.", 
                       help="Text to convert to speech")
    parser.add_argument("--style", default="default", 
                       help="Voice style: default, excited, calm, sad, professional, or a custom instruction")
    parser.add_argument("--output", default="output.wav", 
                       help="Output file (default: output.wav)")
    parser.add_argument("--play", action="store_true", 
                       help="Play the audio after generation")
    return parser.parse_args()

def get_style_instruction(style: str) -> str:
    """Get the voice style instruction based on the style name."""
    style_mapping = {
        "default": "Speak in a natural, warm tone that is friendly and conversational",
        "excited": "Speak with enthusiasm and excitement, like you're sharing great news!",
        "calm": "Speak in a calm, soothing voice like a mindfulness guide",
        "sad": "Speak with a sad and melancholic tone",
        "professional": "Speak in a clear, professional tone like a news anchor",
        "friendly": "Speak in a very friendly and warm tone, like talking to an old friend",
        "customer_service": "Speak like a helpful customer service representative who is ready to assist",
        "teacher": "Speak like a kind, patient teacher explaining a concept to students"
    }
    
    # Return the style instruction if it exists, otherwise use the input as a custom instruction
    return style_mapping.get(style.lower(), style)

def play_audio(audio_data: bytes):
    """Play the generated audio using PyAudio."""
    # Create a temporary file to use with wave
    with open("temp_audio.wav", "wb") as f:
        f.write(audio_data)
    
    # Open the wave file
    wf = wave.open("temp_audio.wav", 'rb')
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open a stream to play the audio
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
    
    # Play the audio in chunks
    chunk_size = 1024
    data = wf.readframes(chunk_size)
    
    print("Playing audio...")
    while data:
        stream.write(data)
        data = wf.readframes(chunk_size)
    
    # Clean up
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf.close()
    os.remove("temp_audio.wav")
    print("Finished playing")

def main():
    """Main function to test OpenAI TTS with voice styles."""
    args = parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key is required. Set via --api-key or OPENAI_API_KEY env var.")
        sys.exit(1)
    
    # Get the voice style instruction
    style_instruction = get_style_instruction(args.style)
    print(f"Using style instruction: \"{style_instruction}\"")
    
    # Configure the OpenAI TTS provider
    provider_config = {
        "api_key": api_key,
        "model": "gpt-4o-mini-tts",
        "voice_style": style_instruction
    }
    
    # Create the TTS provider and service
    try:
        # First register the provider
        provider = TTSProviderFactory.create_provider("openai", config=provider_config)
        
        # Then create a simple TTS service without Redis or Telnyx
        tts_service = TTSService(config={
            "default_provider": "openai",
            "provider_config": {"openai": provider_config}
        })
        
        # Generate speech with the style
        print(f"Generating speech for text: \"{args.text}\"")
        start_time = time.time()
        
        # Use the provider directly or the service
        audio_data = tts_service.generate_with_style(
            text=args.text,
            style=style_instruction
        )
        
        generation_time = time.time() - start_time
        print(f"Speech generation took {generation_time:.2f} seconds")
        
        if not audio_data:
            print("Error: Failed to generate speech")
            sys.exit(1)
            
        # Save the audio to the output file
        with open(args.output, "wb") as f:
            f.write(audio_data)
        print(f"Audio saved to {args.output}")
        
        # Play the audio if requested
        if args.play:
            play_audio(audio_data)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 