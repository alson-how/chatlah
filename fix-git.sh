#!/bin/bash

echo "🔧 Fixing Git Configuration Issues"
echo "=================================="

# Fix 1: Remove git lock file if it exists
if [ -f .git/index.lock ]; then
    echo "Removing stuck git lock file..."
    rm .git/index.lock
fi

# Fix 2: Update remote URL to correct repository with HTTPS
echo "Updating remote URL to correct repository..."
git remote set-url origin https://github.com/elsonng7215-max/chatlah.git

# Fix 3: Update git user configuration to match your GitHub account
echo "Updating git user configuration..."
git config user.name "elsonng7215-max"
git config user.email "elsonng7215@gmail.com"  # Update this to your actual email

# Fix 4: Check current status
echo ""
echo "Current Git Configuration:"
git remote -v
git config user.name
git config user.email

echo ""
echo "✅ Git configuration fixed!"
echo ""
echo "Now you can push with:"
echo "git push -u origin main"
echo ""
echo "When prompted:"
echo "Username: elsonng7215-max"
echo "Password: [your GitHub personal access token]"