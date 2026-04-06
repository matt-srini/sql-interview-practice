#!/bin/sh
cd "$(dirname "$0")/../frontend"
exec /usr/local/bin/node node_modules/.bin/vite --port 5173
