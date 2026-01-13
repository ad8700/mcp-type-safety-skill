#!/bin/bash
# MCP Type Safety Skill Installer for Claude Desktop

set -e

# Show help
show_help() {
    echo "MCP Type Safety Skill Installer"
    echo ""
    echo "Usage: ./install.sh [OPTIONS] [SKILL_DIR]"
    echo ""
    echo "Arguments:"
    echo "  SKILL_DIR    Custom path to Claude skills directory"
    echo ""
    echo "Options:"
    echo "  -h, --help   Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./install.sh                           # Auto-detect skills directory"
    echo "  ./install.sh ~/my-claude-skills        # Use custom directory"
    echo "  ./install.sh /path/to/skills           # Use absolute path"
    echo ""
    echo "Default locations by OS:"
    echo "  macOS:   ~/Documents/Claude/skills"
    echo "  Windows: %USERPROFILE%/Documents/Claude/skills"
    echo "  Linux:   ~/Documents/Claude/skills"
}

# Parse arguments
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Use provided directory or detect from OS
if [[ -n "$1" ]]; then
    SKILL_DIR="$1"
    echo "Using custom skills directory: $SKILL_DIR"
else
    # Detect OS for default location
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SKILL_DIR="$HOME/Documents/Claude/skills"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        SKILL_DIR="$USERPROFILE/Documents/Claude/skills"
    else
        SKILL_DIR="$HOME/Documents/Claude/skills"
    fi
    echo "Auto-detected skills directory: $SKILL_DIR"
fi

# Create directory if needed
mkdir -p "$SKILL_DIR/mcp-type-safety-skill"

# Clone or download the skill
echo ""
echo "Installing MCP Type Safety Skill..."
git clone --quiet https://github.com/ad8700/mcp-type-safety-skill.git temp_clone
cp -r temp_clone/* "$SKILL_DIR/mcp-type-safety-skill/"
rm -rf temp_clone

echo ""
echo "✅ Skill installed successfully!"
echo "📍 Location: $SKILL_DIR/mcp-type-safety-skill"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop"
echo "2. Go to Settings → Skills"
echo "3. Enable 'MCP Type Safety'"
