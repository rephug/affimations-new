"use client";

import { useState, useRef } from "react";

type TTSProvider = "openai" | "spark" | "google" | "azure" | "elevenlabs" | "murf" | "kokoro";

interface VoiceOption {
  id: string;
  name: string;
  provider: TTSProvider;
}

export default function TTSTestingPage() {
  const [text, setText] = useState("Hello, this is a test of the text-to-speech system.");
  const [selectedProvider, setSelectedProvider] = useState<TTSProvider>("openai");
  const [selectedVoice, setSelectedVoice] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Mock voice options for different providers
  const voiceOptions: Record<TTSProvider, VoiceOption[]> = {
    openai: [
      { id: "alloy", name: "Alloy", provider: "openai" },
      { id: "echo", name: "Echo", provider: "openai" },
      { id: "fable", name: "Fable", provider: "openai" },
      { id: "onyx", name: "Onyx", provider: "openai" },
      { id: "nova", name: "Nova", provider: "openai" },
      { id: "shimmer", name: "Shimmer", provider: "openai" },
    ],
    spark: [
      { id: "en_US_kathleen", name: "Kathleen (US)", provider: "spark" },
      { id: "en_US_michael", name: "Michael (US)", provider: "spark" },
      { id: "en_US_emma", name: "Emma (US)", provider: "spark" },
    ],
    google: [
      { id: "en-US-Neural2-A", name: "Female (US)", provider: "google" },
      { id: "en-US-Neural2-D", name: "Male (US)", provider: "google" },
      { id: "en-US-Neural2-F", name: "Female 2 (US)", provider: "google" },
    ],
    azure: [
      { id: "en-US-AriaNeural", name: "Aria (US)", provider: "azure" },
      { id: "en-US-GuyNeural", name: "Guy (US)", provider: "azure" },
      { id: "en-US-JennyNeural", name: "Jenny (US)", provider: "azure" },
    ],
    elevenlabs: [
      { id: "Adam", name: "Adam", provider: "elevenlabs" },
      { id: "Rachel", name: "Rachel", provider: "elevenlabs" },
      { id: "Sam", name: "Sam", provider: "elevenlabs" },
    ],
    murf: [
      { id: "en-US-jacob", name: "Jacob (US)", provider: "murf" },
      { id: "en-US-olivia", name: "Olivia (US)", provider: "murf" },
      { id: "en-US-simon", name: "Simon (UK)", provider: "murf" },
    ],
    kokoro: [
      { id: "en-US-1", name: "Female (US)", provider: "kokoro" },
      { id: "en-US-2", name: "Male (US)", provider: "kokoro" },
      { id: "en-UK-1", name: "Female (UK)", provider: "kokoro" },
    ],
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value as TTSProvider;
    setSelectedProvider(provider);
    // Set the first voice as default when changing provider
    setSelectedVoice(voiceOptions[provider][0].id);
  };

  const handleVoiceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedVoice(e.target.value);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
  };

  const handleGenerateSpeech = async () => {
    if (!text.trim()) return;

    setIsLoading(true);
    setAudioUrl(null);

    try {
      // Replace with actual API call when implemented
      const response = await fetch("/api/tts/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          provider: selectedProvider,
          voice: selectedVoice,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate speech");
      }

      const data = await response.json();
      setAudioUrl(data.audioUrl);

      // Play audio automatically
      if (audioRef.current) {
        audioRef.current.load();
        audioRef.current.play();
      }
    } catch (error) {
      console.error("Error generating speech:", error);
      // In a real app, show a toast or error message
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
        Text-to-Speech Testing
      </h1>

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-6">
        <div className="space-y-4">
          <div>
            <label htmlFor="provider" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              TTS Provider
            </label>
            <select
              id="provider"
              value={selectedProvider}
              onChange={handleProviderChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="openai">OpenAI</option>
              <option value="spark">Spark</option>
              <option value="google">Google</option>
              <option value="azure">Azure</option>
              <option value="elevenlabs">ElevenLabs</option>
              <option value="murf">Murf</option>
              <option value="kokoro">Kokoro</option>
            </select>
          </div>

          <div>
            <label htmlFor="voice" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Voice
            </label>
            <select
              id="voice"
              value={selectedVoice || voiceOptions[selectedProvider][0]?.id}
              onChange={handleVoiceChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              {voiceOptions[selectedProvider].map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="text" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Text to Convert
            </label>
            <textarea
              id="text"
              rows={4}
              value={text}
              onChange={handleTextChange}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Enter text to convert to speech..."
            />
          </div>

          <div>
            <button
              type="button"
              onClick={handleGenerateSpeech}
              disabled={isLoading || !text.trim()}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating...
                </>
              ) : (
                "Generate Speech"
              )}
            </button>
          </div>
        </div>
      </div>

      {audioUrl && (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Generated Audio
          </h2>
          <audio ref={audioRef} controls className="w-full">
            <source src={audioUrl} type="audio/mpeg" />
            Your browser does not support the audio element.
          </audio>
          <div className="mt-4">
            <a
              href={audioUrl}
              download="tts_audio.mp3"
              className="text-primary-600 dark:text-primary-400 hover:underline"
            >
              Download Audio
            </a>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mt-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Provider Information
        </h2>
        <div className="space-y-4">
          <div>
            <h3 className="text-md font-medium text-gray-800 dark:text-gray-200">
              {selectedProvider.charAt(0).toUpperCase() + selectedProvider.slice(1)} TTS
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {selectedProvider === "openai" && "Uses OpenAI's text-to-speech API with natural-sounding voices."}
              {selectedProvider === "spark" && "Spark TTS provides high-quality speech synthesis with natural intonation."}
              {selectedProvider === "google" && "Google's Cloud Text-to-Speech offers a wide range of voices and languages."}
              {selectedProvider === "azure" && "Microsoft Azure's Text-to-Speech service with Neural voices."}
              {selectedProvider === "elevenlabs" && "ElevenLabs offers ultra-realistic AI voice technology."}
              {selectedProvider === "murf" && "Murf.ai provides studio-quality voiceovers with its AI voice generator."}
              {selectedProvider === "kokoro" && "Kokoro TTS offers responsive and natural-sounding voices."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
} 