"use client";

import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Good morning, User
        </h1>
        <button className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500">
          Start New Call
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Today's Affirmation */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Today's Affirmation
            </h3>
            <div className="mt-3 text-gray-700 dark:text-gray-300">
              <p className="text-xl italic">
                "I am capable of amazing things, and today I choose to be my best self."
              </p>
              <p className="mt-2 text-right text-sm text-gray-500 dark:text-gray-400">
                Daily affirmation for May 15, 2023
              </p>
            </div>
          </div>
        </div>

        {/* Upcoming Call */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Upcoming Call
            </h3>
            <div className="mt-3 text-gray-700 dark:text-gray-300">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-lg font-semibold">Morning Check-in</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Today, 8:30 AM
                  </p>
                  <p className="text-sm">Duration: 5 minutes</p>
                </div>
                <button className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
                  Join Call
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Today's Tasks */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                Today's Tasks
              </h3>
              <Link
                href="/tasks"
                className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
              >
                View all
              </Link>
            </div>
            <div className="mt-3 text-gray-700 dark:text-gray-300">
              <ul className="space-y-2">
                <li className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-2">Schedule doctor appointment</span>
                </li>
                <li className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <span className="ml-2">Complete mindfulness exercise</span>
                </li>
                <li className="flex items-center">
                  <input
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    checked
                    readOnly
                  />
                  <span className="ml-2 line-through text-gray-500">Morning call</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Weather */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              Weather
            </h3>
            <div className="mt-3 text-gray-700 dark:text-gray-300">
              <div className="flex items-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-10 w-10 text-yellow-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
                <div className="ml-4">
                  <p className="text-2xl font-bold">72°F</p>
                  <p className="text-sm">Sunny, feels like 75°F</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    San Francisco, CA
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Voice Insights */}
        <div className="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                Voice Insights
              </h3>
              <Link
                href="/voice-insights"
                className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
              >
                View details
              </Link>
            </div>
            <div className="mt-3 text-gray-700 dark:text-gray-300">
              <div className="space-y-2">
                <div>
                  <p className="text-sm">Emotional Level</p>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full"
                      style={{ width: "75%" }}
                    ></div>
                  </div>
                </div>
                <div>
                  <p className="text-sm">Energy Level</p>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div
                      className="bg-green-600 h-2.5 rounded-full"
                      style={{ width: "60%" }}
                    ></div>
                  </div>
                </div>
                <div>
                  <p className="text-sm">Stress Level</p>
                  <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div
                      className="bg-yellow-600 h-2.5 rounded-full"
                      style={{ width: "45%" }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 