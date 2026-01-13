# MCP Type Safety Skill

A Claude skill that validates MCP tool call types before execution, preventing silent failures from type mismatches.

## Overview

Different MCP servers interpret types differently:
- **CloudWatch**: Unix timestamps (seconds)
- **PostgreSQL**: ISO-8601 strings
- **Stripe**: Milliseconds and cents as integers

This skill catches these mismatches **before** they cause problems, providing warnings, auto-fixes, and migration assistance.

## Installation

### Quick Install

```bash
# Clone and run the installer
git clone https://github.com/ad8700/mcp-type-safety-skill.git
cd mcp-type-safety-skill
./install.sh
```

### Custom Install Location

```bash
# Install to a custom skills directory
./install.sh /path/to/your/skills

# Examples
./install.sh ~/my-claude-skills
./install.sh ~/.claude/skills

# Show help and default locations
./install.sh --help
```

**Default locations by OS:**
| OS | Default Path |
|----|--------------|
| macOS | `~/Documents/Claude/skills` |
| Windows | `%USERPROFILE%/Documents/Claude/skills` |
| Linux | `~/Documents/Claude/skills` |

### Manual Installation

#### For Claude Desktop

1. Copy this folder to your Claude skills directory:
   ```bash
   # macOS
   cp -r mcp-type-safety-skill ~/Library/Application\ Support/Claude/skills/

   # Windows
   xcopy /E mcp-type-safety-skill "%APPDATA%\Claude\skills\"

   # Linux
   cp -r mcp-type-safety-skill ~/.config/claude/skills/
   ```

2. Restart Claude Desktop

3. The skill will automatically activate when making MCP tool calls

### For Claude Code (CLI)

1. Reference the skill in your project:
   ```bash
   # Add to .claude/skills/ in your project
   mkdir -p .claude/skills
   cp -r mcp-type-safety-skill .claude/skills/
   ```

2. Or install globally:
   ```bash
   # Add to ~/.claude/skills/
   cp -r mcp-type-safety-skill ~/.claude/skills/
   ```

### Manual Activation

If the skill doesn't auto-activate, you can enable it explicitly:

```
User: Enable the MCP type safety skill

Claude: Type safety validation is now active for all MCP tool calls.
```

## Privacy First

### Everything Stays in Claude

This skill:
- ✅ Runs entirely within your Claude conversation
- ✅ Stores patterns only in current session memory
- ✅ Forgets everything when the conversation ends
- ✅ Never sends data to external servers
- ✅ No telemetry, analytics, or tracking

### What This Skill Sees vs What We See

**What the skill sees** (in your session only):
- Type mismatches you encounter
- Patterns in your MCP usage
- Tools you're calling

**What we see**:
- Absolutely nothing
- Zero telemetry
- No usage statistics
- Only what you choose to share via GitHub issues

### Session-Only Tracking

When the skill shows:
```
📊 Type Safety Report
━━━━━━━━━━━━━━━━━━━━━
MCP Calls Made:     15
Type Issues Found:   3
```

This data:
- Lives only in your current Claude conversation
- Disappears when you start a new chat
- Never leaves your browser/app
- Cannot be accessed by anyone else

### For the Security Conscious
```bash
# This skill has no external dependencies
# No npm packages that phone home
# No Python libraries with telemetry
# Just local validation logic

# Verify yourself - check the code:
cat validator.py | grep -i "request\|http\|telemetry"
# (Should return nothing)
```

### Open Source Accountability

Every line of code is visible at [github.com/ad8700/mcp-type-safety-skill](https://github.com/ad8700/mcp-type-safety-skill)

Found something concerning? Open an issue immediately. Security and privacy are paramount.

### Enterprise Deployment

For organizations with compliance requirements:
- Review the code (it's concise and readable)
- Host your own fork if needed
- Modify to meet your policies
- No external dependencies to audit

Your API schemas, type patterns, and tool usage remain entirely within your control.

## Usage

### Automatic Validation

Once installed, the skill automatically validates every MCP tool call:

```
User: Get user 123 from the database

Claude: Validating database/get_user arguments...

⚠️ user_id: String "123" → Converting to integer 123

Calling database/get_user({"user_id": 123})...

✅ Call successful.
```

### Commands

| Command | Description |
|---------|-------------|
| `check types` | Validate arguments without calling |
| `type report` | Show session statistics |
| `auto-fix on` | Enable automatic type correction |
| `auto-fix off` | Disable auto-fix (ask before fixing) |
| `migration script` | Generate code to fix common issues |
| `explain [field]` | Explain type requirements for a field |

### Example Session

```
User: auto-fix on

Claude: ✅ Auto-fix mode enabled!

User: Query CloudWatch for metrics since "2024-01-01T00:00:00Z"

Claude: 🔧 Auto-fixed: start_time "2024-01-01T00:00:00Z" → 1704067200
✅ Metrics retrieved!

User: type report

Claude:
📊 Type Safety Report
━━━━━━━━━━━━━━━━━━━━━
MCP Calls Made:     5
Type Issues Found:  2
Safety Score: 60% ⚠️

Most Common: Timestamp formats (2)
```

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill definition with behavior instructions |
| `validator.py` | Core validation logic (can be imported in Python) |
| `patterns.json` | Type mismatch patterns and fixes |
| `examples/demo.md` | Detailed usage examples |
| `install.sh` | Auto-installer script |
| `skill.json` | Skill manifest |

## Using validator.py Directly

The validation logic can be used independently:

```python
from validator import (
    validate_tool_arguments,
    check_response_types,
    generate_migration_script,
    SessionStats
)

# Validate tool arguments
report = validate_tool_arguments(
    tool_name="database/get_user",
    arguments={"user_id": "123"},
    schema={
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"}
        }
    }
)

print(report.valid)        # False (has warnings)
print(report.warnings)     # [ValidationResult(...)]
print(report.auto_fixes)   # {"user_id": 123}

# Generate migration code
script = generate_migration_script(report.warnings, language="python")
print(script)

# Track session stats
stats = SessionStats()
stats.total_calls += 1
stats.warnings_issued += len(report.warnings)
print(stats.safety_score())  # 0.0 (100% had warnings)
```

## Pattern Detection

The skill detects these common patterns:

### Timestamp Confusion
```
Unix seconds:      1704067200
Unix milliseconds: 1704067200000
ISO-8601:          "2024-01-01T00:00:00Z"
```

### ID Type Mismatch
```
String ID:  "123"
Integer ID: 123
UUID:       "550e8400-e29b-41d4-a716-446655440000"
```

### Amount Representation
```
Decimal dollars: 15.99
Integer cents:   1599
String cents:    "1599"
```

### Boolean Variants
```
Native:  true / false
String:  "true" / "false"
Integer: 1 / 0
```

## Integration with MCP UP

This skill protects **Claude's MCP calls only**. For system-wide protection:

| Feature | This Skill | MCP UP Proxy |
|---------|-----------|--------------|
| Scope | Claude only | All MCP traffic |
| Validation | Pre-call | Pre and post-call |
| Metrics | Session only | Persistent |
| Enforcement | Advisory | Can block |
| Setup | Just enable | Deploy proxy |

**For production systems**, consider using [MCP Universal Protocol](https://github.com/ad8700/mcp-universal-protocol):

```bash
# Install MCP UP
cd mcp-universal-protocol/prototypes/python
pip install -e .

# Run the proxy
mcp-up start --config config.yaml
```

## Testing

### Test Cases

```python
# Test 1: Valid types pass through
result = validate_tool_arguments(
    "test", {"count": 5}, {"type": "object", "properties": {"count": {"type": "integer"}}}
)
assert result.valid == True
assert len(result.warnings) == 0

# Test 2: Coercible types show warnings
result = validate_tool_arguments(
    "test", {"count": "5"}, {"type": "object", "properties": {"count": {"type": "integer"}}}
)
assert result.valid == True
assert len(result.warnings) == 1
assert result.auto_fixes["count"] == 5

# Test 3: Invalid types prevent calls
result = validate_tool_arguments(
    "test", {"count": "abc"}, {"type": "object", "properties": {"count": {"type": "integer"}}}
)
assert result.valid == False
assert len(result.errors) == 1

# Test 4: Timestamp detection
result = validate_tool_arguments(
    "test", {"created_at": "2024-01-01T00:00:00Z"},
    {"type": "object", "properties": {"created_at": {"type": "integer"}}}
)
assert "timestamp" in result.warnings[0].message.lower() or result.auto_fixes.get("created_at") == 1704067200
```

### Run Tests

```bash
cd mcp-type-safety-skill
python -m pytest test_validator.py -v
```

## Troubleshooting

### Skill Not Activating

1. Check skill is in correct directory
2. Restart Claude
3. Try manual activation: "Enable type safety skill"

### Too Many Warnings

1. Enable auto-fix mode: "auto-fix on"
2. Or disable for specific calls: "skip type check and call..."

### Wrong Auto-Fix

1. Disable auto-fix: "auto-fix off"
2. Report the issue with the specific values

## Contributing

1. Fork the repository
2. Add patterns to `patterns.json`
3. Add tests for new patterns
4. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.

## Links

- [MCP Universal Protocol](https://github.com/ad8700/mcp-universal-protocol)
- [MCP Specification](https://modelcontextprotocol.io/)
