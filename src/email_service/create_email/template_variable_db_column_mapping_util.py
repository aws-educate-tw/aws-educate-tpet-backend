"""
Template Variable to DB Column Mapping Utility

This module provides mappings between email template variables and database columns.
When a template contains specific variables (like "Name" or "姓名"), the corresponding
value from row_data will be mapped to the appropriate database column.

This enables dynamic population of DB columns based on template content.
"""

# Mapping: Template Variables → EMAILS.recipient_name
# The list defines priority order: first match wins
# e.g., if template has both "Name" and "姓名", "Name" will be used
RECIPIENT_NAME_SOURCE_VARIABLES = ["Name", "姓名"]


def map_recipient_name(template_variables: list[str], row_data: dict) -> str | None:
    """
    Map template variables to the `recipient_name` database column.

    This function checks if any of the predefined name-related variables exist
    in both the template and the row data. If found, the corresponding value
    is returned for storage in the `recipient_name` column.

    Priority: Variables earlier in RECIPIENT_NAME_SOURCE_VARIABLES take precedence.

    Args:
        template_variables: List of variable names found in the email template.
        row_data: Dictionary containing the recipient's data.

    Returns:
        The value to store in recipient_name column, or None if no match.

    Example:
        >>> template_variables = ["Email", "Name", "Date"]
        >>> row_data = {"Email": "test@example.com", "Name": "John", "Date": "2024-01-01"}
        >>> map_recipient_name(template_variables, row_data)
        'John'

        >>> # When both "Name" and "姓名" exist, "Name" takes priority
        >>> template_variables = ["Name", "姓名"]
        >>> row_data = {"Name": "John", "姓名": "王小明"}
        >>> map_recipient_name(template_variables, row_data)
        'John'
    """
    for var_name in RECIPIENT_NAME_SOURCE_VARIABLES:
        # Case-sensitive matching
        if var_name in template_variables and var_name in row_data:
            value = row_data.get(var_name)
            if value is not None and str(value).strip():
                return str(value).strip()
    return None
