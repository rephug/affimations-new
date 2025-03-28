import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-b from-primary-50 to-secondary-50 dark:from-primary-950 dark:to-secondary-950">
      <div className="z-10 w-full max-w-5xl items-center justify-center font-mono text-sm flex flex-col">
        <div className="animate-fade-in rounded-lg bg-white/30 dark:bg-black/30 p-8 backdrop-blur-md shadow-lg">
          <h1 className="text-4xl md:text-6xl font-bold text-center bg-gradient-to-r from-primary-600 to-accent-500 bg-clip-text text-transparent">
            Morning Coffee
          </h1>
          <p className="mt-4 text-lg md:text-xl text-center text-gray-700 dark:text-gray-300">
            Your personalized voice assistant for better mornings
          </p>
          <div className="mt-8 flex flex-col md:flex-row gap-4 justify-center">
            <Link 
              href="/login" 
              className="px-6 py-3 rounded-md bg-primary-600 text-white hover:bg-primary-700 transition-colors text-center font-medium"
            >
              Sign In
            </Link>
            <Link 
              href="/register" 
              className="px-6 py-3 rounded-md bg-white text-primary-600 border border-primary-200 hover:bg-primary-50 transition-colors text-center font-medium"
            >
              Register
            </Link>
            <Link 
              href="/dashboard" 
              className="px-6 py-3 rounded-md bg-accent-600 text-white hover:bg-accent-700 transition-colors text-center font-medium"
            >
              Demo Dashboard
            </Link>
          </div>
        </div>
        
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 w-full">
          <div className="animate-slide-up animate-delay-100 p-6 rounded-lg bg-white dark:bg-gray-800 shadow-md">
            <h2 className="text-xl font-semibold mb-3 text-primary-600 dark:text-primary-400">Daily Affirmations</h2>
            <p className="text-gray-600 dark:text-gray-300">Start your day with positive affirmations, personalized to your goals and mindset.</p>
          </div>
          
          <div className="animate-slide-up animate-delay-200 p-6 rounded-lg bg-white dark:bg-gray-800 shadow-md">
            <h2 className="text-xl font-semibold mb-3 text-primary-600 dark:text-primary-400">Voice Analysis</h2>
            <p className="text-gray-600 dark:text-gray-300">Gain insights into your emotional state and vocal patterns over time.</p>
          </div>
          
          <div className="animate-slide-up animate-delay-300 p-6 rounded-lg bg-white dark:bg-gray-800 shadow-md">
            <h2 className="text-xl font-semibold mb-3 text-primary-600 dark:text-primary-400">Morning Briefing</h2>
            <p className="text-gray-600 dark:text-gray-300">Get a personalized summary of your emails, tasks, weather, and news.</p>
          </div>
        </div>
      </div>
    </main>
  );
} 