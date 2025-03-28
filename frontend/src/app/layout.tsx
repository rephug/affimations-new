import '../styles/globals.css';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata = {
  title: 'Morning Coffee',
  description: 'A system that sends daily affirmations via SMS and enables AI conversation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans bg-gray-50 dark:bg-gray-900`}>
        {children}
      </body>
    </html>
  );
} 