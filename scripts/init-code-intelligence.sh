#!/usr/bin/env bash
# Project Initialization Script
# This script sets up the project with GitNexus for structural analysis and mex for behavioral patterns.
# It also consolidates context files for the main agent and ensures synchronization between tools.

# 1. Initialize GitNexus only if the index doesn't exist
if [ ! -d ".gitnexus" ]; then
    echo "Initializing GitNexus..."
    npx gitnexus setup
    gitnexus analyze --skills
else
    echo "GitNexus already initialized for this repository. Skipping..."
fi

# 2. Initialize mex only if the scaffold doesn't exist
if [ ! -d ".mex" ]; then
    echo "Initializing mex..."
    # Note: npm package is 'promexeus'
    npx promexeus setup 
else
    echo "mex scaffold already exists. Skipping setup..."
fi

# # 3. Consolidate Context Files (Only update if not already redirected)
# if ! grep -q ".mex/ROUTER.md" CLAUDE.md 2>/dev/null; then
#     echo "Updating CLAUDE.md redirection..."
#     echo "Read .mex/ROUTER.md to understand project navigation and patterns." > CLAUDE.md
#     echo "Use GitNexus MCP tools for all structural and impact analysis." >> CLAUDE.md
# fi

echo "Initialization complete. Your project is now set up with GitNexus and mex for code intelligence and behavioral analysis."
echo ""
echo "Next steps:"
echo "  1. Review .mex/ROUTER.md for project structure and navigation."
echo "  2. Use gitnexus (skills or MCP) for structural analysis and impact assessments."
echo "  3. Deploy terraform-ingest workflow skills: terraform-ingest skills install --scope project"
