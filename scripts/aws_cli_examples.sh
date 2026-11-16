#!/usr/bin/env bash
# Aceleași operații ca aplicația Python, dar cu AWS CLI direct pe LocalStack.
# Rulare: bash scripts/aws_cli_examples.sh   (LocalStack trebuie să ruleze)
set -euo pipefail

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_PAGER=""

ENDPOINT="${DYNAMODB_ENDPOINT:-http://localhost:4566}"
TABLE="${TABLE_NAME:-Tasks}"
aws_ddb() { aws --endpoint-url="$ENDPOINT" dynamodb "$@"; }

echo "== 1. create-table (init) =="
aws_ddb create-table \
  --table-name "$TABLE" \
  --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=task_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH AttributeName=task_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --query 'TableDescription.[TableName,TableStatus]' --output text
aws_ddb wait table-exists --table-name "$TABLE"

echo "== 2. put-item (add) =="
aws_ddb put-item --table-name "$TABLE" --item '{
  "user_id": {"S": "ana"}, "task_id": {"S": "cli00001"},
  "title": {"S": "Task creat din AWS CLI"}, "status": {"S": "todo"},
  "created_at": {"S": "2026-11-16T12:00:00Z"}}'
echo "OK"

echo "== 3. get-item (get) =="
aws_ddb get-item --table-name "$TABLE" \
  --key '{"user_id": {"S": "ana"}, "task_id": {"S": "cli00001"}}' --output json

echo "== 4. query (list) =="
aws_ddb query --table-name "$TABLE" \
  --key-condition-expression "user_id = :u" \
  --expression-attribute-values '{":u": {"S": "ana"}}' \
  --query 'Items[].[task_id.S,title.S,status.S]' --output table

echo "== 5. update-item (complete) =="
aws_ddb update-item --table-name "$TABLE" \
  --key '{"user_id": {"S": "ana"}, "task_id": {"S": "cli00001"}}' \
  --update-expression "SET #s = :done" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":done": {"S": "done"}}' \
  --return-values ALL_NEW --query 'Attributes.[task_id.S,status.S]' --output text

echo "== 6. delete-item (delete) =="
aws_ddb delete-item --table-name "$TABLE" \
  --key '{"user_id": {"S": "ana"}, "task_id": {"S": "cli00001"}}'
echo "OK"

echo "== 7. delete-table (drop) =="
aws_ddb delete-table --table-name "$TABLE" --query 'TableDescription.TableName' --output text
