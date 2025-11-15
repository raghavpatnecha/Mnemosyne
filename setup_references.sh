#!/bin/bash
# Setup script to add SurfSense and RAG-Anything as git submodules
# Run this script from the Mnemosyne repository root

set -e  # Exit on error

echo "================================"
echo "Adding Reference Repositories"
echo "================================"

# Check we're in the right directory
if [ ! -d ".git" ]; then
    echo "Error: Must be run from repository root (where .git directory is)"
    exit 1
fi

# Check we're on the right branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "claude/check-mnemosyne-repo-01BswSWffoPM15U89RrZEtNB" ]; then
    echo "Warning: You're on branch '$CURRENT_BRANCH'"
    echo "Expected branch: claude/check-mnemosyne-repo-01BswSWffoPM15U89RrZEtNB"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create references directory if it doesn't exist
mkdir -p references

echo ""
echo "Step 1/3: Adding SurfSense as submodule..."
if [ -d "references/surfsense" ]; then
    echo "  - SurfSense already exists, skipping"
else
    git submodule add https://github.com/DAMG7245/surf-sense.git references/surfsense
    echo "  ✓ SurfSense added"
fi

echo ""
echo "Step 2/3: Adding RAG-Anything as submodule..."
if [ -d "references/rag-anything" ]; then
    echo "  - RAG-Anything already exists, skipping"
else
    git submodule add https://github.com/ictnlp/RAG-Anything.git references/rag-anything
    echo "  ✓ RAG-Anything added"
fi

echo ""
echo "Step 3/3: Initializing and updating submodules..."
git submodule init
git submodule update
echo "  ✓ Submodules updated"

echo ""
echo "================================"
echo "Reference repositories added successfully!"
echo ""
echo "Locations:"
echo "  - SurfSense: references/surfsense/"
echo "  - RAG-Anything: references/rag-anything/"
echo ""
echo "Next steps:"
echo "  1. Commit the changes:"
echo "     git add .gitmodules references/"
echo "     git commit -m 'chore: add SurfSense and RAG-Anything as submodules'"
echo "     git push"
echo ""
echo "  2. Study key files (see references/README.md)"
echo "  3. Start Phase 2 development (see PHASE_2_ROADMAP.md)"
echo "================================"
