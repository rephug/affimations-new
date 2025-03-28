# Morning Coffee Frontend

The frontend application for the Morning Coffee system, built with Next.js, Tailwind CSS, and TypeScript.

## Features

- Dashboard for monitoring daily affirmations, tasks, and voice insights
- TTS testing interface to try different text-to-speech providers
- Voice analysis visualization to track emotional and energy patterns
- Affirmation management system with tagging and favorites
- Responsive design for desktop and mobile devices

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **State Management**: React Hooks, TanStack Query
- **Authentication**: Supabase Auth
- **Data Visualization**: Recharts
- **Type Safety**: TypeScript

## Getting Started

### Prerequisites

- Node.js 18.x or later
- npm or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/morning-coffee.git
   cd morning-coffee/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Edit `.env.local` to include your API keys and backend URL.

4. Start the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── public/          # Static assets
├── src/
│   ├── app/         # Next.js App Router pages and layouts
│   │   ├── (auth)/       # Authentication routes (login, register)
│   │   ├── (dashboard)/  # Dashboard routes
│   │   ├── api/          # API routes
│   ├── components/  # Reusable UI components
│   ├── styles/      # Global styles and Tailwind configuration
│   ├── lib/         # Utility functions and shared logic
│   ├── hooks/       # Custom React hooks
│   ├── types/       # TypeScript type definitions
```

## Development Guidelines

- Follow the component structure in the existing codebase
- Use TypeScript for all new files
- Create responsive designs that work on mobile and desktop
- Use the theme variables defined in globals.css for consistent styling
- Follow the error handling patterns in existing API calls

## Deployment

The application can be deployed using Vercel:

```bash
npm run build
# or
yarn build
```

## API Integration

The frontend connects to the Morning Coffee backend API for:

- TTS generation with multiple providers
- Voice analytics processing
- Scheduled calls and affirmations management

## License

This project is licensed under the MIT License - see the LICENSE file for details.
