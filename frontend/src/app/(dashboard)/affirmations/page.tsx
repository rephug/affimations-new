"use client";

import { useState } from "react";

interface Affirmation {
  id: string;
  text: string;
  date: string;
  favorited: boolean;
  tags: string[];
}

// Mock data for affirmations
const mockAffirmations: Affirmation[] = [
  {
    id: "1",
    text: "I am capable of amazing things, and today I choose to be my best self.",
    date: "2023-05-15",
    favorited: true,
    tags: ["motivation", "self-confidence"],
  },
  {
    id: "2",
    text: "I am grateful for all the opportunities that come my way and make the most of them.",
    date: "2023-05-14",
    favorited: false,
    tags: ["gratitude", "opportunity"],
  },
  {
    id: "3",
    text: "I embrace challenges as opportunities for growth and learning.",
    date: "2023-05-13",
    favorited: true,
    tags: ["growth", "challenges"],
  },
  {
    id: "4",
    text: "My potential to succeed is infinite and I work hard to achieve my goals.",
    date: "2023-05-12",
    favorited: false,
    tags: ["success", "goals"],
  },
  {
    id: "5",
    text: "I release all stress and tension and open myself to peace and positivity.",
    date: "2023-05-11",
    favorited: false,
    tags: ["peace", "stress-relief"],
  },
];

export default function AffirmationsPage() {
  const [affirmations, setAffirmations] = useState<Affirmation[]>(mockAffirmations);
  const [newAffirmation, setNewAffirmation] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "favorites">("all");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const handleToggleFavorite = (id: string) => {
    setAffirmations(
      affirmations.map((aff) =>
        aff.id === id ? { ...aff, favorited: !aff.favorited } : aff
      )
    );
  };

  const handleAddAffirmation = () => {
    if (!newAffirmation.trim()) return;
    
    const today = new Date().toISOString().split("T")[0];
    const newAff: Affirmation = {
      id: Date.now().toString(),
      text: newAffirmation,
      date: today,
      favorited: false,
      tags: ["personal"],
    };
    
    setAffirmations([newAff, ...affirmations]);
    setNewAffirmation("");
  };

  const handleDeleteAffirmation = (id: string) => {
    setAffirmations(affirmations.filter((aff) => aff.id !== id));
  };

  const handleToggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter((t) => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  // Get all unique tags
  const allTags = Array.from(
    new Set(affirmations.flatMap((aff) => aff.tags))
  ).sort();

  // Filter affirmations
  const filteredAffirmations = affirmations.filter((aff) => {
    // Filter by favorites
    if (activeTab === "favorites" && !aff.favorited) {
      return false;
    }
    
    // Filter by tags (if tags are selected)
    if (selectedTags.length > 0 && !selectedTags.some((tag) => aff.tags.includes(tag))) {
      return false;
    }
    
    return true;
  });

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
        My Affirmations
      </h1>

      {/* Add new affirmation */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Create New Affirmation
        </h2>
        <div className="flex flex-col space-y-4">
          <textarea
            rows={3}
            value={newAffirmation}
            onChange={(e) => setNewAffirmation(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            placeholder="Type your affirmation here..."
          />
          <button
            type="button"
            onClick={handleAddAffirmation}
            disabled={!newAffirmation.trim()}
            className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
          >
            Add Affirmation
          </button>
        </div>
      </div>

      {/* Filters and tabs */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center space-y-4 sm:space-y-0">
          <div className="flex space-x-4">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-4 py-2 rounded-md ${
                activeTab === "all"
                  ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                  : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setActiveTab("favorites")}
              className={`px-4 py-2 rounded-md ${
                activeTab === "favorites"
                  ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                  : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
            >
              Favorites
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => handleToggleTag(tag)}
                className={`px-2 py-1 text-xs rounded-full ${
                  selectedTags.includes(tag)
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-100"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                }`}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Affirmations list */}
      <div className="space-y-4">
        {filteredAffirmations.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 text-center">
            <p className="text-gray-600 dark:text-gray-400">
              No affirmations found matching your criteria.
            </p>
          </div>
        ) : (
          filteredAffirmations.map((affirmation) => (
            <div
              key={affirmation.id}
              className="bg-white dark:bg-gray-800 shadow rounded-lg p-6"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="text-lg text-gray-900 dark:text-white">{affirmation.text}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {affirmation.tags.map((tag) => (
                      <span
                        key={tag}
                        className="bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 px-2 py-1 text-xs rounded-full"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(affirmation.date).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleToggleFavorite(affirmation.id)}
                    className="text-gray-400 hover:text-yellow-500 dark:text-gray-500 dark:hover:text-yellow-400"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-6 w-6"
                      fill={affirmation.favorited ? "currentColor" : "none"}
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
                      />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeleteAffirmation(affirmation.id)}
                    className="text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-6 w-6"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
} 