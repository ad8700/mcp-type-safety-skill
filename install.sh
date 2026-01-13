#!/bin/bash
# MCP Type Safety Skill Installer for Claude Desktop

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    SKILL_DIR="$HOME/Documents/Claude/skills"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    SKILL_DIR="$USERPROFILE/Documents/Claude/skills"
else
    SKILL_DIR="$HOME/Documents/Claude/skills"
fi

# Create directory if needed
mkdir -p "$SKILL_DIR"

# Clone or download the skill
echo "Installing MCP Type Safety Skill..."
git clone https://github.com/ad8700/mcp-type-safety-skill.git temp_clone
cp -r temp_clone/* "$SKILL_DIR/mcp-type-safety-skill/"
rm -rf temp_clone

echo "✅ Skill installed successfully!"
echo "📍 Location: $SKILL_DIR/mcp-type-safety-skill"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop"
echo "2. Go to Settings → Skills"
echo "3. Enable 'MCP Type Safety'"
