#!/usr/bin/env python
# Example script for testing OpenAI voice styling with Morning Coffee TTS

import os
import sys
import argparse
import time
import wave
import tempfile
import subprocess
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.tts.tts_service import TTSService
from modules.tts.provider_factory import TTSProviderFactory

# Voice style examples for OpenAI's gpt-4o-mini-tts
VOICE_STYLES = {
    "default": "Speak in a natural, conversational voice",
    "friendly": "Speak in a very friendly and warm tone, like talking to an old friend",
    "professional": "Speak in a clear, professional tone like a news anchor",
    "calm": "Speak in a calm, soothing voice like a mindfulness guide",
    "excited": "Speak with enthusiasm and excitement, like you're sharing great news",
    "sad": "Speak with a sad and melancholic tone",
    "whispering": "Speak in a soft whisper, as if sharing a secret",
    "storyteller": "Speak like a storyteller reading a children's book, with animation and engagement",
    "pirate": "Speak like a pirate, with a gruff, enthusiastic voice saying 'arr' occasionally",
    "robot": "Speak like a robot with a monotone voice and mechanical inflections",
    "elderly": "Speak like an elderly person with a warm, wise voice, speaking slowly",
    "customer_service": "Speak like a helpful customer service representative who is ready to assist",
    "boss": "Speak with authority like a boss or leader giving clear instructions",
    "teacher": "Speak like a kind, patient teacher explaining a concept to students",
    "doctor": "Speak like a caring doctor delivering medical information clearly and compassionately",
    "sports_announcer": "Speak with the energy and excitement of a sports announcer calling a game",
    "meditation": "Speak in an extremely calm and peaceful voice for meditation guidance",
    "radio_dj": "Speak like an upbeat radio DJ introducing songs",
    "news_reporter": "Speak with the clear enunciation and neutral tone of a television news reporter",
    "game_show_host": "Speak with the enthusiasm and energy of a game show host"
}

# Sample texts to demonstrate voices
SAMPLE_TEXTS = {
    "affirmation": "Today is filled with endless possibilities. I am capable, confident, and ready to embrace whatever comes my way.",
    "greeting": "Hello! It's wonderful to meet you. I hope you're having a fantastic day so far.",
    "question": "Would you like to tell me about your morning routine? I'd love to hear how you start your day.",
    "weather": "Good morning! Today will be mostly sunny with a high of 75 degrees. Perfect weather for a walk outside.",
    "reminder": "Don't forget about your meeting at 2 PM today. It's scheduled to last for about an hour.",
    "customer_service": "I'm sorry to hear you're experiencing an issue. Let me help you resolve this problem right away."
}

def play_audio(audio_data: bytes) -> None:
    """
    Play audio data using the available audio player.
    
    Args:
        audio_data (bytes): Audio data to play
    """
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(audio_data)
    
    # Detect OS and play accordingly
    if sys.platform == 'darwin':  # macOS
        subprocess.call(['afplay', temp_file_path])
    elif sys.platform == 'linux':
        subprocess.call(['aplay', temp_file_path])
    elif sys.platform == 'win32':  # Windows
        import winsound
        winsound.PlaySound(temp_file_path, winsound.SND_FILENAME)
    
    # Clean up
    os.unlink(temp_file_path)

def save_audio(audio_data: bytes, filename: str) -> None:
    """
    Save audio data to a file.
    
    Args:
        audio_data (bytes): Audio data to save
        filename (str): Filename to save to
    """
    with open(filename, 'wb') as f:
        f.write(audio_data)
    print(f"Saved audio to {filename}")

def main():
    """Main function to demonstrate OpenAI voice styling."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='OpenAI Voice Styling Example')
    parser.add_argument('--api-key', help='OpenAI API key')
    parser.add_argument('--style', choices=list(VOICE_STYLES.keys()), default='default',
                        help='Voice style to use')
    parser.add_argument('--text', default=None, help='Text to speak')
    parser.add_argument('--sample', choices=list(SAMPLE_TEXTS.keys()), default='greeting',
                        help='Sample text to use')
    parser.add_argument('--save', help='Save audio to file')
    parser.add_argument('--list-styles', action='store_true', help='List available styles')
    args = parser.parse_args()
    
    # List styles if requested
    if args.list_styles:
        print("Available voice styles:")
        for style, description in VOICE_STYLES.items():
            print(f"  {style}: {description}")
        return
    
    # Get API key
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key is required. Provide it with --api-key or set OPENAI_API_KEY environment variable.")
        return
    
    # Get text to speak
    text = args.text or SAMPLE_TEXTS.get(args.sample, "Hello, world!")
    
    # Get voice style
    voice_style = VOICE_STYLES.get(args.style, VOICE_STYLES['default'])
    
    print(f"Using voice style: {args.style}")
    print(f"Speaking text: {text}")
    
    # Initialize OpenAI provider
    provider_config = {
        "api_key": api_key,
        "model": "gpt-4o-mini-tts",
        "voice_style": voice_style
    }
    
    openai_provider = TTSProviderFactory.create_provider("openai", None, provider_config)
    
    # Generate speech
    start_time = time.time()
    print("Generating speech...")
    audio_data = openai_provider.generate_speech(text)
    generation_time = time.time() - start_time
    print(f"Speech generated in {generation_time:.2f} seconds")
    
    # Save audio if requested
    if args.save:
        save_audio(audio_data, args.save)
    
    # Play audio
    print("Playing audio...")
    play_audio(audio_data)

if __name__ == "__main__":
    main()
