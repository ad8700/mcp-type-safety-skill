# MCP Type Safety Skill - Usage Examples

This document shows real-world examples of the skill catching type issues and helping fix them.

---

## Example 1: Timestamp Format Detection

### Scenario
User wants to query CloudWatch metrics but passes an ISO-8601 timestamp to a system expecting Unix seconds.

### Interaction

```
User: Get CloudWatch metrics for instance i-1234567890abcdef0 since "2024-01-01T00:00:00Z"

Skill: I'll validate the types before calling cloudwatch/get_metrics...

⚠️ Timestamp Format Mismatch
   Field: start_time
   Value: "2024-01-01T00:00:00Z"
   Issue: This is an ISO-8601 string, but CloudWatch expects Unix seconds

   Auto-fix: Converting to 1704067200

💡 Why this matters: CloudWatch's API uses Unix timestamps in seconds.
   Passing a string could cause the query to fail or return unexpected results.

Proceeding with corrected arguments:
{
  "instance_id": "i-1234567890abcdef0",
  "start_time": 1704067200
}

✅ Call successful!
```

### Code Generated

```python
from datetime import datetime, timezone

def iso_to_unix(iso_string):
    """Convert ISO-8601 to Unix seconds"""
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return int(dt.timestamp())

# Usage
start_time = iso_to_unix("2024-01-01T00:00:00Z")  # Returns: 1704067200
```

---

## Example 2: String-to-Integer ID Conversion

### Scenario
User queries a PostgreSQL database with a string user ID when the schema expects an integer.

### Interaction

```
User: Get all orders for user "456"

Skill: Validating postgres/query arguments...

⚠️ ID Type Mismatch
   Field: user_id
   Value: "456" (string)
   Expected: integer

   Auto-fix: Converting to 456

This is a common issue when IDs come from URL parameters or form inputs.
Most databases will auto-convert, but explicit integers are safer.

Proceeding with:
{
  "user_id": 456,
  "table": "orders"
}

✅ Query returned 12 orders.
```

### Validation Without Schema

Even without a schema, the skill infers that `user_id` should be an integer:

```python
# Field name ends with "_id" → infer integer type
inferred_type = infer_type_from_field_name("user_id")  # Returns: "integer"
```

---

## Example 3: Amount/Currency Handling

### Scenario
User creates a Stripe charge but passes the amount as decimal dollars instead of cents.

### Interaction

```
User: Create a Stripe charge for $29.99 to customer cus_ABC123

Skill: Validating stripe/create_charge arguments...

⚠️ Amount Format Issue
   Field: amount
   Value: 29.99 (decimal dollars)
   Expected: Integer cents (Stripe API requirement)

   Auto-fix: Converting to 2999

❗ Important: Stripe amounts are always in the smallest currency unit.
   For USD, that's cents. $29.99 = 2999 cents.

   Getting this wrong could charge $2999.00 instead of $29.99!

Proceeding with:
{
  "customer": "cus_ABC123",
  "amount": 2999,
  "currency": "usd"
}

✅ Charge created: ch_1234567890
```

### Migration Script

```python
def dollars_to_cents(amount):
    """Convert dollar amount to cents for Stripe"""
    return int(amount * 100)

def cents_to_dollars(cents):
    """Convert cents to dollars for display"""
    return cents / 100

# Usage
stripe_amount = dollars_to_cents(29.99)  # Returns: 2999
display_amount = cents_to_dollars(2999)   # Returns: 29.99
```

---

## Example 4: Nested Object Validation

### Scenario
User creates a complex order with nested shipping address and multiple items.

### Interaction

```
User: Create an order with shipping to "123 Main St" and 2 items

Skill: Validating orders/create arguments...

Found 3 type considerations:

⚠️ shipping.zip_code: "12345" (string) - OK for US postal codes
⚠️ items[0].quantity: "2" (string) → 2 (integer)
⚠️ items[0].price: "1999" (string cents) → Consider decimal format

Nested validation results:
  ✅ shipping.street: string ✓
  ✅ shipping.city: string ✓
  ⚠️ shipping.zip_code: string (acceptable but consider integer for sorting)
  ⚠️ items[0].quantity: string → integer
  ⚠️ items[0].price: ambiguous format

💡 For items[0].price, is "1999" meant to be:
   A) $19.99 (cents as string) → 19.99
   B) $1999.00 (dollars as string) → 1999.00

Please clarify the intended amount.

User: It's $19.99

Skill: Understood! Converting "1999" to cents integer: 1999

Final arguments:
{
  "shipping": {
    "street": "123 Main St",
    "city": "...",
    "zip_code": "12345"
  },
  "items": [
    {
      "product_id": 101,
      "quantity": 2,
      "price": 1999
    }
  ]
}

✅ Order created: ORD-789
```

---

## Example 5: Array Type Checking

### Scenario
User passes a mixed-type array when the schema expects all integers.

### Interaction

```
User: Get products with IDs [1, "2", 3, "four"]

Skill: Validating products/batch_get arguments...

⚠️ Array Type Issues in 'product_ids':
   [0]: 1 (integer) ✅
   [1]: "2" (string) → 2 (integer)
   [2]: 3 (integer) ✅
   [3]: "four" (string) ❌ Cannot convert to integer

❌ Critical Error at product_ids[3]:
   Value "four" cannot be converted to an integer.

Please provide a valid product ID (e.g., 4).

User: Sorry, that should be 4

Skill: Validating updated arguments...

✅ All types valid!

Proceeding with:
{
  "product_ids": [1, 2, 3, 4]
}

✅ Retrieved 4 products.
```

---

## Example 6: Boolean Variants

### Scenario
User passes boolean values in various formats.

### Interaction

```
User: Update user settings: notifications "true", dark_mode 1, is_active yes

Skill: Validating users/update_settings arguments...

⚠️ Boolean Variants Detected:

   notifications: "true" (string)
   → Converting to true (boolean)

   dark_mode: 1 (integer)
   → Converting to true (boolean)

   is_active: "yes" (string)
   → Converting to true (boolean)

💡 Tip: Use native booleans (true/false) for consistency.
   String and integer representations can cause issues with:
   - JSON serialization
   - Type-strict APIs
   - Database boolean columns

Proceeding with:
{
  "notifications": true,
  "dark_mode": true,
  "is_active": true
}

✅ Settings updated!
```

---

## Example 7: Session Statistics Report

### After Multiple Calls

```
User: Show me the type safety report

Skill:
📊 Type Safety Report
━━━━━━━━━━━━━━━━━━━━━

MCP Calls Made:     8
Type Issues Found:  5
Auto-Fixes Applied: 4
Errors Prevented:   1

Safety Score: 62% ⚠️

Most Common Issues:
  1. Timestamp formats (2 occurrences)
     - CloudWatch: Unix seconds
     - PostgreSQL: ISO-8601 strings

  2. ID type mismatches (2 occurrences)
     - String IDs from URL parameters

  3. Boolean variants (1 occurrence)
     - String "true" instead of boolean

Recommendations:
1. Standardize timestamp format across your stack
2. Parse URL parameters to integers before database queries
3. Use native boolean values in API calls

💡 For system-wide protection, consider MCP Universal Protocol:
   https://github.com/ad8700/mcp-universal-protocol

   It validates ALL MCP traffic, not just Claude's calls.
```

---

## Example 8: Migration Script Generation

### User Requests Help

```
User: I keep having timestamp issues. Can you help me fix them?

Skill: I've noticed 3 timestamp mismatches this session. Here's a migration script:

```python
"""
Timestamp Normalization Utilities
Generated by MCP Type Safety Skill
"""
from datetime import datetime, timezone
from typing import Union

def normalize_timestamp(
    value: Union[int, str],
    target_format: str = "iso8601"
) -> Union[str, int]:
    """
    Convert any timestamp to target format.

    Args:
        value: Unix seconds, milliseconds, or ISO-8601 string
        target_format: "iso8601", "unix_seconds", or "unix_ms"

    Examples:
        >>> normalize_timestamp(1704067200, "iso8601")
        "2024-01-01T00:00:00Z"

        >>> normalize_timestamp("2024-01-01T00:00:00Z", "unix_seconds")
        1704067200
    """
    # Parse input
    if isinstance(value, int):
        if value > 1e11:  # Milliseconds
            dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        else:  # Seconds
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError(f"Cannot parse timestamp: {type(value)}")

    # Convert to target format
    if target_format == "iso8601":
        return dt.isoformat().replace("+00:00", "Z")
    elif target_format == "unix_seconds":
        return int(dt.timestamp())
    elif target_format == "unix_ms":
        return int(dt.timestamp() * 1000)
    else:
        raise ValueError(f"Unknown target format: {target_format}")


# Convenience functions for your stack
def cloudwatch_timestamp(value):
    """Convert to CloudWatch format (Unix seconds)"""
    return normalize_timestamp(value, "unix_seconds")

def postgres_timestamp(value):
    """Convert to PostgreSQL format (ISO-8601)"""
    return normalize_timestamp(value, "iso8601")

def stripe_timestamp(value):
    """Convert to Stripe format (Unix seconds)"""
    return normalize_timestamp(value, "unix_seconds")
```

Would you like me to:
1. Save this to a file?
2. Show the JavaScript version?
3. Explain how to integrate it?
```

---

## Example 9: Auto-Fix Mode

### Enabling Auto-Fix

```
User: Enable auto-fix mode

Skill: ✅ Auto-fix mode enabled!

I'll automatically correct coercible type mismatches without asking.
You'll still see notifications of what was fixed.

To disable: say "auto-fix off"

---

User: Get user "789" from the database

Skill: Calling database/get_user...

🔧 Auto-fixed: user_id "789" → 789 (string to integer)

✅ User retrieved: John Doe (john@example.com)

---

User: auto-fix off

Skill: ✅ Auto-fix mode disabled.

I'll ask before making type corrections.
```

---

## Example 10: Critical Error Prevention

### Unrecoverable Type Mismatch

```
User: Delete user with ID "delete-all-users"

Skill: Validating database/delete_user arguments...

❌ Critical Type Error - Call Blocked

   Field: user_id
   Value: "delete-all-users"
   Expected: integer

   This value cannot be converted to an integer and would cause
   the API call to fail (or worse, be misinterpreted).

This looks like it might be a command injection attempt or a typo.
If you meant to delete a specific user, please provide their numeric ID.

Example: "Delete user with ID 123"

User: Oh sorry, I meant user 42

Skill: Validating database/delete_user arguments...

✅ Types valid!

⚠️ Confirmation: You're about to delete user 42.
   This action cannot be undone.

Proceed? [Yes/No]

User: Yes

Skill: ✅ User 42 deleted successfully.
```

---

## Quick Reference

| Issue | Example | Auto-Fix |
|-------|---------|----------|
| String ID | `"123"` → `123` | ✅ |
| Unix to ISO | `1704067200` → `"2024-01-01T00:00:00Z"` | ✅ |
| ISO to Unix | `"2024-01-01T00:00:00Z"` → `1704067200` | ✅ |
| Cents to dollars | `1599` → `15.99` | ⚠️ Confirm |
| String bool | `"true"` → `true` | ✅ |
| Integer bool | `1` → `true` | ✅ |
| Invalid string | `"abc"` → integer | ❌ Block |
