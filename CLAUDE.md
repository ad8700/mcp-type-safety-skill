# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP Type Safety Skill** is a Claude skill that validates MCP (Model Context Protocol) tool call types before execution, preventing silent failures from type mismatches.

### Core Problem Being Solved

Different MCP servers interpret types differently:
- CloudWatch: Unix timestamps (seconds)
- PostgreSQL: ISO-8601 strings
- Stripe: Milliseconds and cents as integers

This skill catches these mismatches **before** they cause problems, providing warnings, auto-fixes, and migration assistance.

## Repository Structure

```
mcp-type-safety-skill/
├── SKILL.md           # Skill definition with YAML frontmatter
├── validator.py       # Core validation logic
├── patterns.json      # Type mismatch patterns and detection rules
├── skill.json         # Skill manifest
├── install.sh         # Auto-installer for Claude Desktop
├── README.md          # Installation and usage guide
├── LICENSE            # MIT License
├── CLAUDE.md          # This file
└── examples/
    └── demo.md        # Usage examples
```

## Skill Architecture

### Core Components

**SKILL.md**: Skill definition with YAML frontmatter containing:
- `name`: mcp-type-safety
- `description`: Validates types when calling MCP servers
- `tags`: [mcp, type-safety, validation, development, quality]

**validator.py**: Core validation functions:
- `validate_tool_arguments(tool_name, arguments, schema)` - Pre-call validation
- `check_response_types(response, expected_schema)` - Post-call validation
- `detect_pattern(field_name, value, expected_type)` - Pattern detection
- `generate_migration_script(mismatches, language)` - Code generation

**patterns.json**: Detection rules for:
- Timestamp mismatches (Unix seconds/ms vs ISO-8601)
- ID type mismatches (string vs integer)
- Amount formats (dollars vs cents)
- Boolean variants (native vs string vs integer)
- Null handling (null vs empty vs undefined)

**skill.json**: Manifest file with:
- Skill metadata (name, version, description)
- File references
- Supported commands
- Capability declarations

## Pattern Detection

The skill detects these patterns:

| Pattern | Detection | Example |
|---------|-----------|---------|
| `timestamp_mismatch` | Unix seconds/ms vs ISO-8601 | `1704067200` vs `"2024-01-01T00:00:00Z"` |
| `id_type_mismatch` | String vs integer IDs | `"123"` vs `123` |
| `amount_format` | Dollars vs cents | `15.99` vs `1599` |
| `boolean_variant` | Native vs string/int | `true` vs `"true"` vs `1` |
| `null_handling` | null vs empty vs undefined | `null` vs `""` vs missing |

## Smart Field Inference

Infer types from field names when no schema is available:

```python
FIELD_PATTERNS = {
    "integer": [".*_id$", ".*_count$", ".*_total$"],
    "datetime": [".*_at$", ".*_time$", ".*timestamp.*"],
    "number": [".*amount.*", ".*price.*", ".*cost.*"],
    "boolean": ["^is_.*", "^has_.*", ".*_enabled$"]
}
```

## Installation Targets

```bash
# macOS
~/Documents/Claude/skills/

# Windows
%USERPROFILE%\Documents\Claude\skills\

# Linux
~/.config/claude/skills/
```

## Development

### Testing validator.py

```python
from validator import validate_tool_arguments, SessionStats

# Test validation
report = validate_tool_arguments(
    "test_tool",
    {"user_id": "123"},
    {"type": "object", "properties": {"user_id": {"type": "integer"}}}
)
print(report.valid)       # True (coercible)
print(report.warnings)    # [ValidationResult...]
print(report.auto_fixes)  # {"user_id": 123}
```

### Running Tests

```bash
cd mcp-type-safety-skill
python -m pytest test_validator.py -v
```

## Related Projects

- [MCP Universal Protocol](https://github.com/ad8700/mcp-universal-protocol) - Full proxy-based type validation for all MCP traffic (not just Claude)

## Implementation Notes

### Skill vs MCP UP Proxy

| Feature | This Skill | MCP UP Proxy |
|---------|-----------|--------------|
| Scope | Claude only | All MCP traffic |
| Validation | Pre-call | Pre and post-call |
| Metrics | Session only | Persistent |
| Enforcement | Advisory | Can block |
| Setup | Just enable | Deploy proxy |

### skill.json Manifest Format

The `skill.json` file provides machine-readable metadata:

```json
{
  "name": "mcp-type-safety",
  "version": "1.0.0",
  "main": "SKILL.md",
  "files": {
    "skill_definition": "SKILL.md",
    "validator": "validator.py",
    "patterns": "patterns.json"
  },
  "capabilities": ["pre-call-validation", "auto-fix", "session-tracking"],
  "commands": [{"name": "check types", "description": "..."}]
}
```

### Cross-Platform Install Script

The `install.sh` script detects the OS and installs to the appropriate location:

```bash
# OS Detection
if [[ "$OSTYPE" == "darwin"* ]]; then
    SKILL_DIR="$HOME/Documents/Claude/skills"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    SKILL_DIR="$USERPROFILE/Documents/Claude/skills"
else
    SKILL_DIR="$HOME/Documents/Claude/skills"
fi
```

**Note**: On Windows with Git Bash/MINGW64, `$OSTYPE` is `msys`.

### Validator Design Decisions

1. **Severity Enum**: Uses Python Enum for type safety
   - `VALID`, `WARNING`, `ERROR`, `SUGGESTION`

2. **Dataclasses**: All data models use `@dataclass` for clean structure
   - `ValidationResult`, `ValidationReport`, `SessionStats`

3. **Field Pattern Inference**: When no schema provided, infers types from field names
   - `*_id` → integer
   - `*_at` → datetime
   - `is_*` → boolean

4. **Auto-Fix Priority**: Coercion is attempted in this order:
   - String → Integer (for IDs)
   - ISO-8601 → Unix timestamp (for dates)
   - Boolean variants → native boolean

### Origin and History

This skill was extracted from `mcp-universal-protocol/skills/mcp-type-safety-skill/` into a standalone repository to:
1. Allow independent installation
2. Enable simpler contribution workflow
3. Provide a focused, single-purpose package

The validation logic in `validator.py` is derived from the MCP UP proxy's validation engine but simplified for skill-only use (no async, no network I/O).

### Git Workflow

- Main branch: `main`
- Line endings: CRLF warnings are normal on Windows (configured in .gitattributes)
- Repository: https://github.com/ad8700/mcp-type-safety-skill
