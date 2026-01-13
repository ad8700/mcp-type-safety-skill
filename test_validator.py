"""
Unit tests for MCP Type Safety Validator

Run with: python -m pytest test_validator.py -v
"""

import pytest
from validator import (
    Severity,
    ValidationResult,
    ValidationReport,
    SessionStats,
    get_actual_type,
    infer_type_from_field_name,
    looks_like_unix_timestamp,
    looks_like_iso8601,
    looks_like_cents_string,
    detect_pattern,
    try_coerce,
    validate_tool_arguments,
    check_response_types,
    generate_migration_script,
    format_report_text,
    format_session_report,
)


class TestGetActualType:
    """Tests for get_actual_type function"""

    def test_null_type(self):
        assert get_actual_type(None) == "null"

    def test_boolean_type(self):
        assert get_actual_type(True) == "boolean"
        assert get_actual_type(False) == "boolean"

    def test_integer_type(self):
        assert get_actual_type(123) == "integer"
        assert get_actual_type(0) == "integer"
        assert get_actual_type(-42) == "integer"

    def test_number_type(self):
        assert get_actual_type(3.14) == "number"
        assert get_actual_type(0.0) == "number"
        assert get_actual_type(-2.5) == "number"

    def test_string_type(self):
        assert get_actual_type("hello") == "string"
        assert get_actual_type("") == "string"

    def test_array_type(self):
        assert get_actual_type([1, 2, 3]) == "array"
        assert get_actual_type([]) == "array"

    def test_object_type(self):
        assert get_actual_type({"key": "value"}) == "object"
        assert get_actual_type({}) == "object"

    def test_boolean_not_integer(self):
        """Booleans should not be detected as integers"""
        assert get_actual_type(True) != "integer"
        assert get_actual_type(False) != "integer"


class TestInferTypeFromFieldName:
    """Tests for infer_type_from_field_name function"""

    def test_integer_patterns(self):
        assert infer_type_from_field_name("user_id") == "integer"
        assert infer_type_from_field_name("userId") == "integer"
        assert infer_type_from_field_name("USER_ID") == "integer"
        assert infer_type_from_field_name("id") == "integer"
        assert infer_type_from_field_name("item_count") == "integer"
        assert infer_type_from_field_name("order_total") == "integer"

    def test_datetime_patterns(self):
        assert infer_type_from_field_name("created_at") == "datetime"
        assert infer_type_from_field_name("start_time") == "datetime"
        assert infer_type_from_field_name("timestamp") == "datetime"
        assert infer_type_from_field_name("birth_date") == "datetime"

    def test_number_patterns(self):
        assert infer_type_from_field_name("total_amount") == "number"
        assert infer_type_from_field_name("price") == "number"
        assert infer_type_from_field_name("unit_cost") == "number"
        assert infer_type_from_field_name("tax_rate") == "number"

    def test_boolean_patterns(self):
        assert infer_type_from_field_name("is_active") == "boolean"
        assert infer_type_from_field_name("has_permission") == "boolean"
        assert infer_type_from_field_name("can_edit") == "boolean"
        assert infer_type_from_field_name("feature_enabled") == "boolean"

    def test_no_match(self):
        assert infer_type_from_field_name("random_field") is None
        assert infer_type_from_field_name("data") is None
        assert infer_type_from_field_name("value") is None


class TestLooksLikeUnixTimestamp:
    """Tests for looks_like_unix_timestamp function"""

    def test_valid_unix_seconds(self):
        assert looks_like_unix_timestamp(1704067200) is True  # 2024-01-01
        assert looks_like_unix_timestamp(1000000000) is True  # 2001-09-09
        assert looks_like_unix_timestamp(2000000000) is True  # 2033-05-18

    def test_valid_unix_milliseconds(self):
        assert looks_like_unix_timestamp(1704067200000) is True
        assert looks_like_unix_timestamp(1000000000000) is True

    def test_invalid_timestamps(self):
        assert looks_like_unix_timestamp(123) is False
        assert looks_like_unix_timestamp(999999999) is False  # Too small
        assert looks_like_unix_timestamp(3000000000) is False  # Too large


class TestLooksLikeIso8601:
    """Tests for looks_like_iso8601 function"""

    def test_full_iso8601(self):
        assert looks_like_iso8601("2024-01-01T00:00:00Z") is True
        assert looks_like_iso8601("2024-01-01T12:30:45.123Z") is True

    def test_date_only(self):
        assert looks_like_iso8601("2024-01-01") is True

    def test_space_separator(self):
        assert looks_like_iso8601("2024-01-01 12:30:45") is True

    def test_invalid_formats(self):
        assert looks_like_iso8601("01-01-2024") is False
        assert looks_like_iso8601("January 1, 2024") is False
        assert looks_like_iso8601("1704067200") is False


class TestLooksLikeCentsString:
    """Tests for looks_like_cents_string function"""

    def test_valid_cents(self):
        assert looks_like_cents_string("1599", "total_amount") is True
        assert looks_like_cents_string("100", "price") is True
        assert looks_like_cents_string("9999", "item_cost") is True

    def test_non_money_field(self):
        assert looks_like_cents_string("1599", "user_count") is False

    def test_non_numeric_string(self):
        assert looks_like_cents_string("abc", "amount") is False
        assert looks_like_cents_string("15.99", "amount") is False


class TestDetectPattern:
    """Tests for detect_pattern function"""

    def test_timestamp_mismatch_unix_to_string(self):
        pattern = detect_pattern("created_at", 1704067200, "string")
        assert pattern == "timestamp_mismatch"

    def test_timestamp_mismatch_iso_to_integer(self):
        pattern = detect_pattern("timestamp", "2024-01-01T00:00:00Z", "integer")
        assert pattern == "timestamp_mismatch"

    def test_id_type_mismatch(self):
        pattern = detect_pattern("user_id", "123", "integer")
        assert pattern == "id_type_mismatch"

    def test_amount_format(self):
        pattern = detect_pattern("total_amount", "1599", "number")
        assert pattern == "amount_format"

    def test_boolean_variant_string(self):
        pattern = detect_pattern("is_active", "true", "boolean")
        assert pattern == "boolean_variant"

    def test_boolean_variant_integer(self):
        pattern = detect_pattern("enabled", 1, "boolean")
        assert pattern == "boolean_variant"

    def test_null_handling(self):
        assert detect_pattern("field", None, "string") == "null_handling"
        assert detect_pattern("field", "", "string") == "null_handling"
        assert detect_pattern("field", "null", "string") == "null_handling"


class TestTryCoerce:
    """Tests for try_coerce function"""

    def test_same_type(self):
        success, value, msg = try_coerce(123, "integer")
        assert success is True
        assert value == 123

    def test_string_to_integer(self):
        success, value, msg = try_coerce("123", "integer")
        assert success is True
        assert value == 123

    def test_string_to_integer_fail(self):
        success, value, msg = try_coerce("abc", "integer")
        assert success is False

    def test_string_to_number(self):
        success, value, msg = try_coerce("3.14", "number")
        assert success is True
        assert value == 3.14

    def test_integer_to_number(self):
        success, value, msg = try_coerce(42, "number")
        assert success is True
        assert value == 42.0

    def test_boolean_from_string_true(self):
        success, value, msg = try_coerce("true", "boolean")
        assert success is True
        assert value is True

    def test_boolean_from_string_false(self):
        success, value, msg = try_coerce("false", "boolean")
        assert success is True
        assert value is False

    def test_boolean_from_integer(self):
        success, value, msg = try_coerce(1, "boolean")
        assert success is True
        assert value is True

        success, value, msg = try_coerce(0, "boolean")
        assert success is True
        assert value is False

    def test_integer_to_string(self):
        success, value, msg = try_coerce(123, "string")
        assert success is True
        assert value == "123"

    def test_unix_to_iso8601(self):
        """Unix timestamps are converted to ISO-8601 when target is string"""
        success, value, msg = try_coerce(1704067200, "string")
        assert success is True
        assert "2024-01-01" in value
        assert "T00:00:00" in value

    def test_iso8601_to_unix(self):
        """ISO-8601 strings are converted to Unix timestamps when target is integer"""
        success, value, msg = try_coerce("2024-01-01T00:00:00Z", "integer")
        assert success is True
        assert value == 1704067200

    def test_non_timestamp_integer_to_string(self):
        """Regular integers (not timestamps) convert to plain strings"""
        success, value, msg = try_coerce(123, "string")
        assert success is True
        assert value == "123"


class TestValidateToolArguments:
    """Tests for validate_tool_arguments function"""

    def test_valid_types_with_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"}
            }
        }
        report = validate_tool_arguments("test", {"count": 5}, schema)
        assert report.valid is True
        assert len(report.warnings) == 0
        assert len(report.errors) == 0

    def test_coercible_type_with_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"}
            }
        }
        report = validate_tool_arguments("test", {"count": "5"}, schema)
        assert report.valid is True
        assert len(report.warnings) == 1
        assert report.auto_fixes["count"] == 5

    def test_invalid_type_with_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"}
            }
        }
        report = validate_tool_arguments("test", {"count": "abc"}, schema)
        assert report.valid is False
        assert len(report.errors) == 1

    def test_missing_required_field(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        report = validate_tool_arguments("test", {}, schema)
        assert report.valid is False
        assert len(report.errors) == 1
        assert "missing" in report.errors[0].message.lower()

    def test_unknown_field_suggestion(self):
        schema = {
            "type": "object",
            "properties": {}
        }
        report = validate_tool_arguments("test", {"unknown": "value"}, schema)
        assert report.valid is True
        assert len(report.suggestions) == 1

    def test_field_inference_without_schema(self):
        report = validate_tool_arguments("test", {"user_id": "123"}, None)
        assert report.valid is True
        assert len(report.warnings) == 1
        assert report.auto_fixes["user_id"] == 123

    def test_multiple_types_in_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "integer"]}
            }
        }
        report = validate_tool_arguments("test", {"value": "hello"}, schema)
        assert report.valid is True

        report = validate_tool_arguments("test", {"value": 42}, schema)
        assert report.valid is True

    def test_timestamp_detection(self):
        """ISO-8601 strings are auto-converted to Unix timestamps"""
        schema = {
            "type": "object",
            "properties": {
                "created_at": {"type": "integer"}
            }
        }
        report = validate_tool_arguments(
            "test",
            {"created_at": "2024-01-01T00:00:00Z"},
            schema
        )
        assert report.valid is True
        assert len(report.warnings) == 1
        assert report.auto_fixes.get("created_at") == 1704067200


class TestCheckResponseTypes:
    """Tests for check_response_types function"""

    def test_matching_types(self):
        schema = {
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"}
            }
        }
        response = {"name": "test", "count": 5}
        report = check_response_types(response, schema)
        assert report.valid is True
        assert len(report.warnings) == 0

    def test_mismatched_type(self):
        schema = {
            "properties": {
                "count": {"type": "integer"}
            }
        }
        response = {"count": "5"}
        report = check_response_types(response, schema)
        assert len(report.warnings) == 1

    def test_no_schema(self):
        report = check_response_types({"any": "data"}, None)
        assert report.valid is True

    def test_non_dict_response(self):
        schema = {"properties": {"x": {"type": "integer"}}}
        report = check_response_types("not a dict", schema)
        assert report.valid is True


class TestSessionStats:
    """Tests for SessionStats class"""

    def test_initial_safety_score(self):
        stats = SessionStats()
        assert stats.safety_score() == 100.0

    def test_safety_score_with_warnings(self):
        stats = SessionStats()
        stats.total_calls = 10
        stats.warnings_issued = 2
        assert stats.safety_score() == 80.0

    def test_safety_score_with_errors(self):
        stats = SessionStats()
        stats.total_calls = 10
        stats.errors_prevented = 5
        assert stats.safety_score() == 50.0

    def test_safety_score_minimum(self):
        stats = SessionStats()
        stats.total_calls = 5
        stats.warnings_issued = 10  # More warnings than calls
        assert stats.safety_score() == 0.0

    def test_to_dict(self):
        stats = SessionStats()
        stats.total_calls = 5
        result = stats.to_dict()
        assert "total_calls" in result
        assert "safety_score" in result
        assert result["total_calls"] == 5


class TestGenerateMigrationScript:
    """Tests for generate_migration_script function"""

    def test_python_script_generation(self):
        mismatches = [
            ValidationResult(
                field="user_id",
                severity=Severity.WARNING,
                message="Convert string to integer",
                value="123",
                expected_type="integer",
                actual_type="string",
                auto_fix=123
            )
        ]
        script = generate_migration_script(mismatches, "python")
        assert "def convert_id" in script
        assert "user_id" in script

    def test_javascript_script_generation(self):
        mismatches = [
            ValidationResult(
                field="user_id",
                severity=Severity.WARNING,
                message="Convert string to integer",
                value="123",
                expected_type="integer",
                actual_type="string",
                auto_fix=123
            )
        ]
        script = generate_migration_script(mismatches, "javascript")
        assert "function convertId" in script

    def test_unsupported_language(self):
        script = generate_migration_script([], "rust")
        assert "Unsupported language" in script

    def test_timestamp_migration(self):
        mismatches = [
            ValidationResult(
                field="created_at",
                severity=Severity.WARNING,
                message="Convert timestamp",
                value=1704067200,
                expected_type="string",
                actual_type="integer",
                suggestion="timestamp conversion",
                auto_fix="2024-01-01T00:00:00Z"
            )
        ]
        script = generate_migration_script(mismatches, "python")
        assert "normalize_timestamp" in script


class TestFormatReportText:
    """Tests for format_report_text function"""

    def test_all_valid(self):
        report = ValidationReport(valid=True)
        text = format_report_text(report, "test_tool")
        assert "All types valid" in text

    def test_with_errors(self):
        report = ValidationReport(valid=False)
        report.errors.append(ValidationResult(
            field="test",
            severity=Severity.ERROR,
            message="Test error",
            value="bad",
            expected_type="integer",
            actual_type="string"
        ))
        text = format_report_text(report, "test_tool")
        assert "error" in text.lower()

    def test_with_warnings(self):
        report = ValidationReport(valid=True)
        report.warnings.append(ValidationResult(
            field="test",
            severity=Severity.WARNING,
            message="Test warning",
            value="123",
            expected_type="integer",
            actual_type="string",
            auto_fix=123
        ))
        text = format_report_text(report, "test_tool")
        assert "warning" in text.lower()


class TestFormatSessionReport:
    """Tests for format_session_report function"""

    def test_basic_report(self):
        stats = SessionStats()
        stats.total_calls = 10
        stats.warnings_issued = 2
        text = format_session_report(stats)
        assert "Type Safety Report" in text
        assert "10" in text

    def test_report_with_patterns(self):
        stats = SessionStats()
        stats.total_calls = 5
        stats.patterns_detected["timestamp_mismatch"] = 3
        text = format_session_report(stats)
        assert "Timestamp Mismatch" in text

    def test_safety_score_emoji(self):
        stats = SessionStats()
        stats.total_calls = 10
        stats.warnings_issued = 1  # 90% score
        text = format_session_report(stats)
        assert "✅" in text


class TestValidationReportToDict:
    """Tests for ValidationReport.to_dict method"""

    def test_empty_report(self):
        report = ValidationReport(valid=True)
        result = report.to_dict()
        assert result["valid"] is True
        assert result["warnings"] == []
        assert result["errors"] == []

    def test_report_with_data(self):
        report = ValidationReport(valid=True)
        report.warnings.append(ValidationResult(
            field="test",
            severity=Severity.WARNING,
            message="msg",
            value="v",
            expected_type="int",
            actual_type="str"
        ))
        report.auto_fixes["test"] = 123
        result = report.to_dict()
        assert len(result["warnings"]) == 1
        assert result["auto_fixes"]["test"] == 123
