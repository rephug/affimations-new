"use client";

import { useState } from "react";

interface VoiceData {
  date: string;
  emotionalLevel: number;
  energyLevel: number;
  stressLevel: number;
  primaryEmotion: string;
  secondaryEmotion: string;
  audioLength: number;
  notes: string;
}

// Mock data for voice insights
const mockVoiceData: VoiceData[] = [
  {
    date: "2023-05-15",
    emotionalLevel: 75,
    energyLevel: 60,
    stressLevel: 45,
    primaryEmotion: "Optimistic",
    secondaryEmotion: "Confident",
    audioLength: 120,
    notes: "Morning call showed good energy and positive outlook.",
  },
  {
    date: "2023-05-14",
    emotionalLevel: 65,
    energyLevel: 70,
    stressLevel: 30,
    primaryEmotion: "Enthusiastic",
    secondaryEmotion: "Focused",
    audioLength: 95,
    notes: "Higher energy than usual with clear articulation.",
  },
  {
    date: "2023-05-13",
    emotionalLevel: 40,
    energyLevel: 35,
    stressLevel: 75,
    primaryEmotion: "Concerned",
    secondaryEmotion: "Tired",
    audioLength: 105,
    notes: "Voice patterns indicate fatigue and some stress.",
  },
  {
    date: "2023-05-12",
    emotionalLevel: 80,
    energyLevel: 85,
    stressLevel: 25,
    primaryEmotion: "Cheerful",
    secondaryEmotion: "Excited",
    audioLength: 135,
    notes: "Very positive call with high energy and enthusiasm.",
  },
  {
    date: "2023-05-11",
    emotionalLevel: 60,
    energyLevel: 55,
    stressLevel: 50,
    primaryEmotion: "Contemplative",
    secondaryEmotion: "Calm",
    audioLength: 110,
    notes: "Balanced emotional state with moderate energy levels.",
  },
];

export default function VoiceInsightsPage() {
  const [voiceData, setVoiceData] = useState<VoiceData[]>(mockVoiceData);
  const [selectedDate, setSelectedDate] = useState<string | null>(mockVoiceData[0].date);
  const [timeframe, setTimeframe] = useState<"week" | "month" | "year">("week");

  // Get selected entry
  const selectedEntry = selectedDate 
    ? voiceData.find((entry) => entry.date === selectedDate) 
    : null;

  // Calculate averages for the selected timeframe
  const getAverages = () => {
    const filteredData = voiceData.slice(0, timeframe === "week" ? 7 : timeframe === "month" ? 30 : 365);
    
    if (filteredData.length === 0) return { emotion: 0, energy: 0, stress: 0 };
    
    const emotion = filteredData.reduce((sum, entry) => sum + entry.emotionalLevel, 0) / filteredData.length;
    const energy = filteredData.reduce((sum, entry) => sum + entry.energyLevel, 0) / filteredData.length;
    const stress = filteredData.reduce((sum, entry) => sum + entry.stressLevel, 0) / filteredData.length;
    
    return { emotion, energy, stress };
  };

  const averages = getAverages();

  // Get emotion color
  const getEmotionColor = (emotion: string) => {
    const emotionColors: Record<string, string> = {
      "Optimistic": "text-green-500",
      "Confident": "text-blue-500",
      "Enthusiastic": "text-yellow-500",
      "Focused": "text-indigo-500",
      "Concerned": "text-orange-500",
      "Tired": "text-gray-500",
      "Cheerful": "text-pink-500",
      "Excited": "text-purple-500",
      "Contemplative": "text-teal-500",
      "Calm": "text-blue-400",
    };
    
    return emotionColors[emotion] || "text-gray-700 dark:text-gray-300";
  };

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
        Voice Insights
      </h1>

      {/* Timeframe selection */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-4 mb-6">
        <div className="flex space-x-4">
          <button
            onClick={() => setTimeframe("week")}
            className={`px-4 py-2 rounded-md ${
              timeframe === "week"
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            Last Week
          </button>
          <button
            onClick={() => setTimeframe("month")}
            className={`px-4 py-2 rounded-md ${
              timeframe === "month"
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            Last Month
          </button>
          <button
            onClick={() => setTimeframe("year")}
            className={`px-4 py-2 rounded-md ${
              timeframe === "year"
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            Last Year
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Summary metrics */}
        <div className="col-span-full bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Summary
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
              <h3 className="text-sm text-gray-500 dark:text-gray-400">
                Average Emotional Level
              </h3>
              <div className="mt-2 flex justify-between items-end">
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {averages.emotion.toFixed(1)}%
                </p>
                <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
                  <div 
                    className="h-full bg-blue-600 rounded-full"
                    style={{ width: `${averages.emotion}%` }}
                  ></div>
                </div>
              </div>
            </div>

            <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4">
              <h3 className="text-sm text-gray-500 dark:text-gray-400">
                Average Energy Level
              </h3>
              <div className="mt-2 flex justify-between items-end">
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {averages.energy.toFixed(1)}%
                </p>
                <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
                  <div 
                    className="h-full bg-green-600 rounded-full"
                    style={{ width: `${averages.energy}%` }}
                  ></div>
                </div>
              </div>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-900/30 rounded-lg p-4">
              <h3 className="text-sm text-gray-500 dark:text-gray-400">
                Average Stress Level
              </h3>
              <div className="mt-2 flex justify-between items-end">
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {averages.stress.toFixed(1)}%
                </p>
                <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
                  <div 
                    className="h-full bg-yellow-600 rounded-full"
                    style={{ width: `${averages.stress}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Voice data list */}
        <div className="md:col-span-1 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Voice Entries
          </h2>
          <div className="space-y-3">
            {voiceData.map((entry) => (
              <button
                key={entry.date}
                onClick={() => setSelectedDate(entry.date)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  selectedDate === entry.date 
                    ? "bg-primary-100 dark:bg-primary-900/50 border-l-4 border-primary-500" 
                    : "bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium">
                    {new Date(entry.date).toLocaleDateString(undefined, { 
                      month: 'short', 
                      day: 'numeric'
                    })}
                  </span>
                  <span className={getEmotionColor(entry.primaryEmotion)}>
                    {entry.primaryEmotion}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Voice entry details */}
        <div className="md:col-span-2 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Voice Details
          </h2>
          
          {selectedEntry ? (
            <div className="space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-semibold">
                    {new Date(selectedEntry.date).toLocaleDateString(undefined, { 
                      weekday: 'long',
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric'
                    })}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Audio Length: {Math.floor(selectedEntry.audioLength / 60)}:{(selectedEntry.audioLength % 60).toString().padStart(2, '0')}
                  </p>
                </div>
                <button className="bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300 px-3 py-1 rounded-md text-sm">
                  Play Recording
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Emotional Level</p>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div 
                      className="bg-blue-600 h-2.5 rounded-full"
                      style={{ width: `${selectedEntry.emotionalLevel}%` }}
                    ></div>
                  </div>
                  <p className="mt-1 text-sm font-medium">{selectedEntry.emotionalLevel}%</p>
                </div>
                
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Energy Level</p>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div 
                      className="bg-green-600 h-2.5 rounded-full" 
                      style={{ width: `${selectedEntry.energyLevel}%` }}
                    ></div>
                  </div>
                  <p className="mt-1 text-sm font-medium">{selectedEntry.energyLevel}%</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Stress Level</p>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div 
                      className="bg-yellow-600 h-2.5 rounded-full" 
                      style={{ width: `${selectedEntry.stressLevel}%` }}
                    ></div>
                  </div>
                  <p className="mt-1 text-sm font-medium">{selectedEntry.stressLevel}%</p>
                </div>

                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Primary Emotion</p>
                  <p className={`text-lg font-medium ${getEmotionColor(selectedEntry.primaryEmotion)}`}>
                    {selectedEntry.primaryEmotion}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Secondary: {selectedEntry.secondaryEmotion}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Notes</p>
                <p className="mt-1 text-gray-700 dark:text-gray-300">{selectedEntry.notes}</p>
              </div>

              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Recommendations</h4>
                <ul className="list-disc pl-5 text-gray-700 dark:text-gray-300 space-y-1">
                  {selectedEntry.stressLevel > 60 && (
                    <li>Consider practicing mindfulness or breathing exercises to reduce stress levels.</li>
                  )}
                  {selectedEntry.energyLevel < 40 && (
                    <li>Your energy levels are low. Consider adjusting your sleep schedule or incorporating short walks.</li>
                  )}
                  {selectedEntry.emotionalLevel > 70 && (
                    <li>Your emotional positivity is excellent! Use this positive outlook to tackle challenging tasks.</li>
                  )}
                  {selectedEntry.emotionalLevel < 50 && (
                    <li>Try gratitude journaling to improve emotional outlook.</li>
                  )}
                  <li>Schedule your next call during your typical high-energy period to maximize productivity.</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              Select a voice entry to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 