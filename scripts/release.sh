#!/bin/bash

# Exit on any error
set -e

# Change to the project root directory
cd "$(dirname "$0")/.."

if [ -z "$1" ]; then
    echo "❌ Error: No version specified."
    echo "Usage: ./scripts/release.sh <new_version>"
    echo "Example: ./scripts/release.sh 1.0.0"
    exit 1
fi

# Extract the version without the 'v' prefix if we included it (e.g., v1.0.0 -> 1.0.0)
RAW_VERSION=${1#v}
NEW_VERSION=$RAW_VERSION
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

echo "🦅 [Talons] Starting release process for version $NEW_VERSION on branch $CURRENT_BRANCH..."

# 1. Ensure scripts are executable
echo "📝 Ensuring build scripts are executable..."
chmod +x build/*.sh plugin/*.sh plugin/*.py scripts/*.sh 2>/dev/null || true

# 3. Validate build locally
echo "🔨 Building release locally to validate..."
./scripts/make.sh

# 4. Create git tag
echo "🏷️ Creating git tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo ""
echo "✅ Talons release v$NEW_VERSION is ready!"
echo "☁️ To complete the release, push the tag to GitHub:"
echo "  git push origin \"v$NEW_VERSION\""
echo ""
echo "✅ Once pushed, GitHub Actions will package talons.gda using uv and publish the release automatically."
