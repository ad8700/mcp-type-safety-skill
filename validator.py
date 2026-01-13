"""
MCP Type Safety Validator

Core validation logic for the MCP Type Safety Skill.
Provides type checking, pattern detection, and migration assistance.
"""

import re
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Validation severity levels"""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    SUGGESTION = "suggestion"


@dataclass
class ValidationResult:
    """Result of a single field validation"""
    field: str
    severity: Severity
    message: str
    value: Any
    expected_type: str
    actual_type: str
    suggestion: Optional[str] = None
    auto_fix: Optional[Any] = None


@dataclass
class ValidationReport:
    """Complete validation report for a tool call"""
    valid: bool
    warnings: List[ValidationResult] = field(default_factory=list)
    errors: List[ValidationResult] = field(default_factory=list)
    suggestions: List[ValidationResult] = field(default_factory=list)
    auto_fixes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "warnings": [w.__dict__ for w in self.warnings],
            "errors": [e.__dict__ for e in self.errors],
            "suggestions": [s.__dict__ for s in self.suggestions],
            "auto_fixes": self.auto_fixes
        }


@dataclass
class SessionStats:
    """Track validation statistics across a session"""
    total_calls: int = 0
    validated_calls: int = 0
    warnings_issued: int = 0
    errors_prevented: int = 0
    auto_fixes_applied: int = 0
    patterns_detected: Dict[str, int] = field(default_factory=lambda: {
        "timestamp_mismatch": 0,
        "id_type_mismatch": 0,
        "amount_format": 0,
        "boolean_variant": 0,
        "null_handling": 0
    })

    def safety_score(self) -> float:
        """Calculate type safety score (0-100)"""
        if self.total_calls == 0:
            return 100.0
        clean_calls = self.total_calls - self.warnings_issued - self.errors_prevented
        return max(0, (clean_calls / self.total_calls) * 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "validated_calls": self.validated_calls,
            "warnings_issued": self.warnings_issued,
            "errors_prevented": self.errors_prevented,
            "auto_fixes_applied": self.auto_fixes_applied,
            "patterns_detected": self.patterns_detected,
            "safety_score": self.safety_score()
        }


# Field name patterns for smart type inference
FIELD_PATTERNS = {
    "integer": [
        r".*_id$", r".*Id$", r".*ID$",
        r".*_count$", r".*_total$", r".*_num$",
        r"^id$", r"^count$", r"^total$", r"^num$"
    ],
    "datetime": [
        r".*_at$", r".*_time$", r".*timestamp.*",
        r"^created$", r"^updated$", r"^deleted$",
        r".*_date$"
    ],
    "number": [
        r".*amount.*", r".*price.*", r".*cost.*",
        r".*_rate$", r".*_percent.*", r".*_ratio.*"
    ],
    "boolean": [
        r"^is_.*", r"^has_.*", r"^can_.*",
        r".*_enabled$", r".*_active$", r".*_flag$"
    ]
}


def get_actual_type(value: Any) -> str:
    """Get the JSON type name for a Python value"""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "unknown"


def infer_type_from_field_name(field_name: str) -> Optional[str]:
    """Infer expected type from field name patterns"""
    for expected_type, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, field_name, re.IGNORECASE):
                return expected_type
    return None


def looks_like_unix_timestamp(value: int) -> bool:
    """Check if an integer looks like a Unix timestamp"""
    # Unix seconds: 1000000000 to 2500000000 (roughly 2001 to 2049)
    # Unix milliseconds: 1000000000000 to 2500000000000
    return (1_000_000_000 <= value <= 2_500_000_000 or
            1_000_000_000_000 <= value <= 2_500_000_000_000)


def looks_like_iso8601(value: str) -> bool:
    """Check if a string looks like an ISO-8601 timestamp"""
    iso_patterns = [
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # Basic ISO-8601
        r"^\d{4}-\d{2}-\d{2}$",  # Date only
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # Space separator
    ]
    return any(re.match(p, value) for p in iso_patterns)


def looks_like_cents_string(value: str, field_name: str) -> bool:
    """Check if a string looks like cents (for amount fields)"""
    if not re.match(r"^\d+$", value):
        return False
    # Check if field name suggests money
    money_patterns = ["amount", "price", "cost", "total", "fee", "charge"]
    return any(p in field_name.lower() for p in money_patterns)


def detect_pattern(field_name: str, value: Any, expected_type: str) -> Optional[str]:
    """Identify common type mismatch patterns"""
    actual_type = get_actual_type(value)

    # Timestamp confusion
    if expected_type == "string" and actual_type == "integer":
        if looks_like_unix_timestamp(value):
            return "timestamp_mismatch"

    if expected_type == "integer" and actual_type == "string":
        if looks_like_iso8601(value):
            return "timestamp_mismatch"

    # ID type mismatch
    if "id" in field_name.lower():
        if expected_type == "integer" and actual_type == "string":
            return "id_type_mismatch"

    # Amount format
    if actual_type == "string" and looks_like_cents_string(value, field_name):
        return "amount_format"

    # Boolean variants
    if expected_type == "boolean":
        if value in ["true", "false", "True", "False", "1", "0", 1, 0]:
            return "boolean_variant"

    # Null handling
    if value in [None, "", "null", "undefined", "None"]:
        return "null_handling"

    return None


def try_coerce(value: Any, target_type: str) -> Tuple[bool, Any, str]:
    """
    Attempt to coerce a value to target type.
    Returns: (success, coerced_value, message)
    """
    actual_type = get_actual_type(value)

    if actual_type == target_type:
        return True, value, "Types match"

    # String to integer
    if target_type == "integer" and actual_type == "string":
        try:
            coerced = int(value)
            return True, coerced, f'Convert string "{value}" to integer {coerced}'
        except ValueError:
            return False, value, f'Cannot convert "{value}" to integer'

    # String to number
    if target_type == "number" and actual_type == "string":
        try:
            coerced = float(value)
            return True, coerced, f'Convert string "{value}" to number {coerced}'
        except ValueError:
            return False, value, f'Cannot convert "{value}" to number'

    # Integer to number (always valid)
    if target_type == "number" and actual_type == "integer":
        return True, float(value), "Integer is valid as number"

    # Boolean variants
    if target_type == "boolean":
        if value in [1, "1", "true", "True", "yes", "Yes"]:
            return True, True, f'Convert "{value}" to true'
        if value in [0, "0", "false", "False", "no", "No"]:
            return True, False, f'Convert "{value}" to false'

    # Integer to string
    if target_type == "string" and actual_type in ["integer", "number"]:
        return True, str(value), f"Convert {value} to string"

    # Timestamp conversions
    if target_type == "string" and actual_type == "integer":
        if looks_like_unix_timestamp(value):
            # Convert Unix timestamp to ISO-8601
            ts = value / 1000 if value > 1e11 else value
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            iso_str = dt.isoformat().replace("+00:00", "Z")
            return True, iso_str, f"Convert Unix timestamp to ISO-8601: {iso_str}"

    if target_type == "integer" and actual_type == "string":
        if looks_like_iso8601(value):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                unix_ts = int(dt.timestamp())
                return True, unix_ts, f"Convert ISO-8601 to Unix timestamp: {unix_ts}"
            except ValueError:
                pass

    return False, value, f"Cannot coerce {actual_type} to {target_type}"


def validate_tool_arguments(
    tool_name: str,
    arguments: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None
) -> ValidationReport:
    """
    Validate tool arguments against schema.

    Args:
        tool_name: Name of the MCP tool being called
        arguments: Arguments being passed to the tool
        schema: JSON Schema for the tool's input (optional)

    Returns:
        ValidationReport with warnings, errors, and suggestions
    """
    report = ValidationReport(valid=True)

    if not schema:
        # No schema - use field name inference
        for field_name, value in arguments.items():
            inferred_type = infer_type_from_field_name(field_name)
            if inferred_type:
                actual_type = get_actual_type(value)
                if actual_type != inferred_type:
                    can_coerce, coerced, message = try_coerce(value, inferred_type)
                    pattern = detect_pattern(field_name, value, inferred_type)

                    if can_coerce:
                        result = ValidationResult(
                            field=field_name,
                            severity=Severity.WARNING,
                            message=message,
                            value=value,
                            expected_type=inferred_type,
                            actual_type=actual_type,
                            suggestion=f"Consider using {inferred_type} type",
                            auto_fix=coerced
                        )
                        report.warnings.append(result)
                        report.auto_fixes[field_name] = coerced
                    else:
                        result = ValidationResult(
                            field=field_name,
                            severity=Severity.ERROR,
                            message=message,
                            value=value,
                            expected_type=inferred_type,
                            actual_type=actual_type
                        )
                        report.errors.append(result)
                        report.valid = False
        return report

    # Validate against schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for req_field in required:
        if req_field not in arguments:
            report.errors.append(ValidationResult(
                field=req_field,
                severity=Severity.ERROR,
                message=f"Required field '{req_field}' is missing",
                value=None,
                expected_type=properties.get(req_field, {}).get("type", "unknown"),
                actual_type="missing"
            ))
            report.valid = False

    # Check each argument
    for field_name, value in arguments.items():
        if field_name not in properties:
            # Unknown field - just note it
            report.suggestions.append(ValidationResult(
                field=field_name,
                severity=Severity.SUGGESTION,
                message=f"Field '{field_name}' not in schema",
                value=value,
                expected_type="unknown",
                actual_type=get_actual_type(value),
                suggestion="This field may be ignored by the server"
            ))
            continue

        field_schema = properties[field_name]
        expected_type = field_schema.get("type")

        if not expected_type:
            continue

        # Handle multiple types
        if isinstance(expected_type, list):
            actual_type = get_actual_type(value)
            if actual_type not in expected_type:
                can_coerce = False
                for t in expected_type:
                    success, _, _ = try_coerce(value, t)
                    if success:
                        can_coerce = True
                        break
                if not can_coerce:
                    report.errors.append(ValidationResult(
                        field=field_name,
                        severity=Severity.ERROR,
                        message=f"Type '{actual_type}' not in allowed types {expected_type}",
                        value=value,
                        expected_type=str(expected_type),
                        actual_type=actual_type
                    ))
                    report.valid = False
            continue

        actual_type = get_actual_type(value)

        if actual_type != expected_type:
            can_coerce, coerced, message = try_coerce(value, expected_type)
            pattern = detect_pattern(field_name, value, expected_type)

            if can_coerce:
                result = ValidationResult(
                    field=field_name,
                    severity=Severity.WARNING,
                    message=message,
                    value=value,
                    expected_type=expected_type,
                    actual_type=actual_type,
                    auto_fix=coerced
                )
                report.warnings.append(result)
                report.auto_fixes[field_name] = coerced
            else:
                result = ValidationResult(
                    field=field_name,
                    severity=Severity.ERROR,
                    message=message,
                    value=value,
                    expected_type=expected_type,
                    actual_type=actual_type
                )
                report.errors.append(result)
                report.valid = False

    return report


def check_response_types(
    response: Any,
    expected_schema: Optional[Dict[str, Any]] = None
) -> ValidationReport:
    """
    Check if response matches expected types.

    Args:
        response: Response data from MCP tool call
        expected_schema: Expected JSON Schema for the response

    Returns:
        ValidationReport with any type issues found
    """
    report = ValidationReport(valid=True)

    if not expected_schema or not isinstance(response, dict):
        return report

    properties = expected_schema.get("properties", {})

    for field_name, value in response.items():
        if field_name not in properties:
            continue

        expected_type = properties[field_name].get("type")
        if not expected_type:
            continue

        actual_type = get_actual_type(value)

        if isinstance(expected_type, list):
            if actual_type not in expected_type:
                report.warnings.append(ValidationResult(
                    field=field_name,
                    severity=Severity.WARNING,
                    message=f"Response field '{field_name}' has unexpected type",
                    value=value,
                    expected_type=str(expected_type),
                    actual_type=actual_type
                ))
        elif actual_type != expected_type:
            pattern = detect_pattern(field_name, value, expected_type)
            report.warnings.append(ValidationResult(
                field=field_name,
                severity=Severity.WARNING,
                message=f"Response field '{field_name}' has type '{actual_type}', expected '{expected_type}'",
                value=value,
                expected_type=expected_type,
                actual_type=actual_type,
                suggestion=f"Pattern detected: {pattern}" if pattern else None
            ))

    return report


def generate_migration_script(
    mismatches: List[ValidationResult],
    language: str = "python"
) -> str:
    """
    Generate code to fix common type issues.

    Args:
        mismatches: List of validation results with type mismatches
        language: Target language ("python" or "javascript")

    Returns:
        Migration script as a string
    """
    if language == "python":
        return _generate_python_migration(mismatches)
    elif language == "javascript":
        return _generate_javascript_migration(mismatches)
    else:
        return f"# Unsupported language: {language}"


def _generate_python_migration(mismatches: List[ValidationResult]) -> str:
    """Generate Python migration script"""
    lines = [
        '"""',
        'Type Migration Script',
        'Generated by MCP Type Safety Skill',
        '"""',
        '',
        'from datetime import datetime, timezone',
        'from typing import Any, Union',
        '',
    ]

    # Collect unique conversions needed
    conversions = set()
    for m in mismatches:
        conversions.add((m.actual_type, m.expected_type))

    # Generate conversion functions
    if ("string", "integer") in conversions or ("integer", "string") in conversions:
        lines.extend([
            'def convert_id(value: Union[str, int]) -> int:',
            '    """Convert string ID to integer"""',
            '    if isinstance(value, int):',
            '        return value',
            '    return int(value)',
            '',
        ])

    if any("timestamp" in str(m.suggestion or "").lower() for m in mismatches):
        lines.extend([
            'def normalize_timestamp(value, target_format="iso8601"):',
            '    """Convert any timestamp to target format"""',
            '    if isinstance(value, int):',
            '        # Unix timestamp (seconds or milliseconds)',
            '        if value > 1e11:  # Milliseconds',
            '            value = value / 1000',
            '        dt = datetime.fromtimestamp(value, tz=timezone.utc)',
            '    elif isinstance(value, str):',
            '        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))',
            '    else:',
            '        raise ValueError(f"Cannot parse timestamp: {value}")',
            '',
            '    if target_format == "iso8601":',
            '        return dt.isoformat().replace("+00:00", "Z")',
            '    elif target_format == "unix_seconds":',
            '        return int(dt.timestamp())',
            '    elif target_format == "unix_ms":',
            '        return int(dt.timestamp() * 1000)',
            '    else:',
            '        raise ValueError(f"Unknown format: {target_format}")',
            '',
        ])

    if ("string", "number") in conversions:
        lines.extend([
            'def convert_amount(value: str, from_cents: bool = True) -> float:',
            '    """Convert string amount to decimal"""',
            '    num = float(value)',
            '    if from_cents:',
            '        return num / 100',
            '    return num',
            '',
        ])

    if ("string", "boolean") in conversions or ("integer", "boolean") in conversions:
        lines.extend([
            'def convert_boolean(value: Any) -> bool:',
            '    """Convert various boolean representations"""',
            '    if isinstance(value, bool):',
            '        return value',
            '    if isinstance(value, int):',
            '        return value != 0',
            '    if isinstance(value, str):',
            '        return value.lower() in ("true", "1", "yes")',
            '    return bool(value)',
            '',
        ])

    # Generate example usage
    lines.extend([
        '# Example usage:',
        '# arguments = {',
    ])

    for m in mismatches:
        if m.auto_fix is not None:
            lines.append(f'#     "{m.field}": {repr(m.auto_fix)},  # was: {repr(m.value)}')

    lines.append('# }')

    return '\n'.join(lines)


def _generate_javascript_migration(mismatches: List[ValidationResult]) -> str:
    """Generate JavaScript migration script"""
    lines = [
        '/**',
        ' * Type Migration Script',
        ' * Generated by MCP Type Safety Skill',
        ' */',
        '',
    ]

    conversions = set()
    for m in mismatches:
        conversions.add((m.actual_type, m.expected_type))

    if ("string", "integer") in conversions:
        lines.extend([
            'function convertId(value) {',
            '  return typeof value === "string" ? parseInt(value, 10) : value;',
            '}',
            '',
        ])

    if any("timestamp" in str(m.suggestion or "").lower() for m in mismatches):
        lines.extend([
            'function normalizeTimestamp(value, targetFormat = "iso8601") {',
            '  let date;',
            '  if (typeof value === "number") {',
            '    // Unix timestamp (seconds or milliseconds)',
            '    const ms = value > 1e11 ? value : value * 1000;',
            '    date = new Date(ms);',
            '  } else if (typeof value === "string") {',
            '    date = new Date(value);',
            '  } else {',
            '    throw new Error(`Cannot parse timestamp: ${value}`);',
            '  }',
            '',
            '  switch (targetFormat) {',
            '    case "iso8601":',
            '      return date.toISOString();',
            '    case "unix_seconds":',
            '      return Math.floor(date.getTime() / 1000);',
            '    case "unix_ms":',
            '      return date.getTime();',
            '    default:',
            '      throw new Error(`Unknown format: ${targetFormat}`);',
            '  }',
            '}',
            '',
        ])

    if ("string", "number") in conversions:
        lines.extend([
            'function convertAmount(value, fromCents = true) {',
            '  const num = parseFloat(value);',
            '  return fromCents ? num / 100 : num;',
            '}',
            '',
        ])

    lines.extend([
        '// Example usage:',
        '// const arguments = {',
    ])

    for m in mismatches:
        if m.auto_fix is not None:
            lines.append(f'//   {m.field}: {json.dumps(m.auto_fix)},  // was: {json.dumps(m.value)}')

    lines.append('// };')

    return '\n'.join(lines)


def format_report_text(report: ValidationReport, tool_name: str) -> str:
    """Format validation report as human-readable text"""
    lines = [f"Validating {tool_name} arguments...", ""]

    if not report.warnings and not report.errors and not report.suggestions:
        lines.append("✅ All types valid!")
        return '\n'.join(lines)

    if report.errors:
        lines.append(f"❌ Found {len(report.errors)} error(s):")
        for err in report.errors:
            lines.append(f"   {err.field}: {err.message}")
        lines.append("")

    if report.warnings:
        lines.append(f"⚠️ Found {len(report.warnings)} warning(s):")
        for warn in report.warnings:
            lines.append(f"   {warn.field}: {warn.actual_type} → {warn.expected_type}")
            if warn.auto_fix is not None:
                lines.append(f"      Auto-fix: {repr(warn.value)} → {repr(warn.auto_fix)}")
        lines.append("")

    if report.suggestions:
        lines.append(f"💡 {len(report.suggestions)} suggestion(s):")
        for sug in report.suggestions:
            lines.append(f"   {sug.field}: {sug.suggestion or sug.message}")

    if report.auto_fixes:
        lines.append("")
        lines.append("Corrected arguments:")
        lines.append(json.dumps(report.auto_fixes, indent=2))

    return '\n'.join(lines)


def format_session_report(stats: SessionStats) -> str:
    """Format session statistics as human-readable text"""
    score = stats.safety_score()
    score_emoji = "✅" if score >= 80 else "⚠️" if score >= 50 else "❌"

    lines = [
        "📊 Type Safety Report",
        "━" * 24,
        "",
        f"MCP Calls Made:     {stats.total_calls}",
        f"Type Issues Found:  {stats.warnings_issued}",
        f"Auto-Fixes Applied: {stats.auto_fixes_applied}",
        f"Errors Prevented:   {stats.errors_prevented}",
        "",
        f"Safety Score: {score:.0f}% {score_emoji}",
        "",
    ]

    # Most common issues
    patterns = [(k, v) for k, v in stats.patterns_detected.items() if v > 0]
    if patterns:
        patterns.sort(key=lambda x: x[1], reverse=True)
        lines.append("Most Common Issues:")
        for i, (pattern, count) in enumerate(patterns[:3], 1):
            name = pattern.replace("_", " ").title()
            lines.append(f"  {i}. {name} ({count} occurrence{'s' if count > 1 else ''})")
        lines.append("")

    lines.extend([
        "💡 Tip: For system-wide type safety, consider using MCP Universal Protocol.",
        "   It validates ALL MCP traffic, not just Claude's calls.",
        "   → https://github.com/ad8700/mcp-universal-protocol"
    ])

    return '\n'.join(lines)
