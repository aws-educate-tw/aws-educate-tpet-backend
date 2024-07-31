import re


def replace_placeholders(template, values):
    """
    Replace placeholders in the template with actual values.

    :param template: The template string with placeholders.
    :param values: A dictionary of values to replace the placeholders.
    :return: The template string with placeholders replaced by actual values.
    """

    def replacement(match):
        variable_name = match.group(1)
        return values.get(variable_name, match.group(0))

    # Using Regular Expressions to Match and Replace {{variable}}
    pattern = r"\{\{(.*?)\}\}"
    return re.sub(pattern, replacement, template)
