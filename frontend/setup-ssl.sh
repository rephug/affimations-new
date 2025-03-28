#!/bin/bash

set -e

echo "------------------------------------"
echo "Morning Coffee SSL Setup Script"
echo "------------------------------------"

echo "Obtaining SSL certificate for morningcoffee.aireeaa.com..."
sudo certbot --nginx -d morningcoffee.aireeaa.com

echo "------------------------------------"
echo "SSL certificate should now be installed."
echo "You can access the Morning Coffee application at: https://morningcoffee.aireeaa.com"
echo "------------------------------------" 