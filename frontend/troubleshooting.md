# Morning Coffee Application Troubleshooting Guide

## Current Status

1. ✅ SSL Certificate Setup: SSL certificates for `morningcoffee.aireeaa.com` have been properly configured. The "not secure" error is fixed.

2. ✅ Nginx Configuration: Nginx is correctly configured to proxy requests to the Next.js application running on port 3000. The "502 Bad Gateway" error is fixed.

3. ❌ Next.js Routing: The testing pages are not being properly recognized by the Next.js application, resulting in 404 errors.

## Next.js Routing Issue Troubleshooting Steps

### Step 1: Verify all testing pages are properly formatted

Make sure all page components follow the correct Next.js conventions:

1. For client-side components, ensure they have `'use client';` at the top of the file.
2. For pages that should be accessible directly, make sure they export a default function component.

Example of a correct page.tsx file:

```tsx
'use client';

import React from 'react';

export default function TestingPage() {
  return (
    <div>
      <h1>Testing Page</h1>
    </div>
  );
}
```

### Step 2: Check directory structure

Make sure the directory structure follows Next.js App Router conventions:

```
src/
├── app/
│   ├── testing/
│   │   ├── page.tsx   # Route: /testing
│   │   ├── layout.tsx  # (optional)
│   │   ├── voice-test/
│   │   │   ├── page.tsx  # Route: /testing/voice-test
```

### Step 3: Clear the cache and rebuild

Sometimes Next.js caching can cause issues with new routes. Try:

```bash
cd /home/adminrob/projects/affimations/frontend
sudo rm -rf .next
sudo npm run build
sudo pm2 restart morning-coffee-frontend
```

### Step 4: Check for route conflicts

Make sure there are no conflicts with other route configurations, such as middleware or custom route configs.

### Step 5: Update static files

After rebuilding, make sure to update the static files:

```bash
sudo mkdir -p /var/www/morning-coffee/static/_next/static
sudo cp -R /home/adminrob/projects/affimations/frontend/.next/static/* /var/www/morning-coffee/static/_next/static/
```

### Step 6: Check Next.js debug output

If the issue persists, you can enable debug output for Next.js to see detailed routing information:

```bash
cd /home/adminrob/projects/affimations/frontend
sudo NODE_OPTIONS="--inspect" pm2 restart morning-coffee-frontend
```

## Temporary Workaround

If the routing issue can't be resolved immediately, you can create a static HTML page as a temporary solution:

1. Create a static HTML file for the testing page
2. Place it in `/var/www/morning-coffee/html/testing/index.html`
3. Update the Nginx configuration to serve this file for the /testing path

```nginx
location = /testing {
    root /var/www/morning-coffee/html;
    try_files /testing/index.html =404;
}
```

Then restart Nginx:

```bash
sudo systemctl restart nginx
```

## Need Further Assistance?

If none of these steps resolve the issue, please consider:

1. Consulting the Next.js documentation: https://nextjs.org/docs
2. Posting a question on Stack Overflow with the next.js and routing tags
3. Opening an issue on the Next.js GitHub repository if you believe it's a bug

Remember to include details about your Next.js version, configuration, and directory structure when seeking help. 