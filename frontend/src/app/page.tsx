export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="max-w-5xl w-full text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
          Morning Coffee
        </h1>
        <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-300">
          A system that sends daily affirmations via SMS, calls users to have them repeat the affirmation, 
          and enables AI conversation using advanced voice technologies.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <a
            href="/dashboard"
            className="rounded-md bg-primary-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
          >
            Go to Dashboard
          </a>
          <a href="/login" className="text-sm font-semibold leading-6 text-gray-900 dark:text-white">
            Log in <span aria-hidden="true">→</span>
          </a>
        </div>
      </div>
    </main>
  );
} 