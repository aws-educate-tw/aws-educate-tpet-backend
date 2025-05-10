#!/bin/bash
set -e

# Validate input parameters
if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <RESOURCE_ARN> <SECRET_ARN> <DATABASE> <AWS_REGION>"
  exit 1
fi

RESOURCE_ARN="$1"
SECRET_ARN="$2"
DATABASE="$3"
AWS_REGION="$4" 
SQL_FILE="init-schema.sql"

# 1) Convert Windows CRLF (if any) to LF.
#    On macOS/BSD, we need the '' after -i. On Linux, -i '' *may* fail,
#    so see the cross-platform note below if you need a universal fix.
sed -i '' 's/\r$//' "$SQL_FILE" 2>/dev/null || true

# 2) Flatten all newlines into a single space for consistent splitting.
sql=$(tr '\n' ' ' < "$SQL_FILE")

# 3) Split on semicolons.
IFS=';' read -ra statements <<< "$sql"

echo "Found ${#statements[@]} statements in $SQL_FILE"
for stmt in "${statements[@]}"; do
  # Trim leading/trailing whitespace.
  stmt=$(echo "$stmt" | sed 's/^[ \t]*//;s/[ \t]*$//')

  # Only execute non-empty statements.
  if [[ -n "$stmt" ]]; then
    echo "Executing: [$stmt]"
    aws rds-data execute-statement \
      --region "$AWS_REGION" \
      --resource-arn "$RESOURCE_ARN" \
      --secret-arn "$SECRET_ARN" \
      --database "$DATABASE" \
      --sql "$stmt"
  fi
done