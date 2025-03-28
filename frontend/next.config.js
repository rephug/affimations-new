/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  // Ensure that static files are copied correctly
  distDir: '.next',
  // Add custom configuration for experimental features
  experimental: {
    // No experimental options needed
  },
  // Configure redirects and rewrites if needed
  async rewrites() {
    return [
      // Ensure testing routes are handled properly
      {
        source: '/testing/voice-test',
        destination: '/testing/voice-test',
      },
      {
        source: '/testing/call-test',
        destination: '/testing/call-test',
      },
    ];
  },
};

module.exports = nextConfig; 