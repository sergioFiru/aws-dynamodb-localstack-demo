#!/usr/bin/env bash
# Aceleași operații ca aplicația Python, dar cu AWS CLI direct pe LocalStack.
# Rulare: bash scripts/aws_cli_examples.sh   (LocalStack trebuie să ruleze)
set -euo pipefail

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_PAGER=""

ENDPOINT="${DYNAMODB_ENDPOINT:-http://localhost:4566}"
TABLE="${TABLE_NAME:-Grades}"
aws_ddb() { aws --endpoint-url="$ENDPOINT" dynamodb "$@"; }
KEY='{"student_id": {"S": "S1"}, "course_id": {"S": "C1"}}'

echo "== 1. create-table (init) =="
aws_ddb create-table \
  --table-name "$TABLE" \
  --attribute-definitions AttributeName=student_id,AttributeType=S AttributeName=course_id,AttributeType=S \
  --key-schema AttributeName=student_id,KeyType=HASH AttributeName=course_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --query 'TableDescription.[TableName,TableStatus]' --output text
aws_ddb wait table-exists --table-name "$TABLE"

echo "== 2. put-item (add, refuză duplicatele) =="
for c in 'C1:Retele:9' 'C2:Baze de date:8'; do
  IFS=: read -r cid name grade <<< "$c"
  aws_ddb put-item --table-name "$TABLE" \
    --condition-expression "attribute_not_exists(student_id)" \
    --item "{\"student_id\": {\"S\": \"S1\"}, \"course_id\": {\"S\": \"$cid\"},
             \"course_name\": {\"S\": \"$name\"}, \"grade\": {\"N\": \"$grade\"},
             \"semester\": {\"S\": \"2026-1\"}, \"updated_at\": {\"S\": \"2026-11-16T12:00:00Z\"}}"
  echo "OK: S1 / $cid / nota $grade"
done

echo "== 3. put-item duplicat (eroare așteptată) =="
aws_ddb put-item --table-name "$TABLE" \
  --condition-expression "attribute_not_exists(student_id)" \
  --item '{"student_id": {"S": "S1"}, "course_id": {"S": "C1"}, "course_name": {"S": "Retele"},
           "grade": {"N": "5"}, "semester": {"S": "2026-1"}, "updated_at": {"S": "2026-11-16T12:00:00Z"}}' \
  2>&1 || echo "-> duplicat refuzat, cum era de așteptat"

echo "== 4. get-item (get) =="
aws_ddb get-item --table-name "$TABLE" --key "$KEY" \
  --query 'Item.[student_id.S,course_id.S,course_name.S,grade.N,semester.S]' --output text

echo "== 5. query (list) =="
aws_ddb query --table-name "$TABLE" \
  --key-condition-expression "student_id = :s" \
  --expression-attribute-values '{":s": {"S": "S1"}}' \
  --query 'Items[].[course_id.S,course_name.S,grade.N,semester.S]' --output table

echo "== 6. update-item (update) =="
aws_ddb update-item --table-name "$TABLE" --key "$KEY" \
  --update-expression "SET grade = :g, updated_at = :u" \
  --condition-expression "attribute_exists(student_id)" \
  --expression-attribute-values '{":g": {"N": "10"}, ":u": {"S": "2026-11-16T13:00:00Z"}}' \
  --return-values ALL_NEW --query 'Attributes.[course_id.S,grade.N,updated_at.S]' --output text

echo "== 7. delete-item (delete) =="
aws_ddb delete-item --table-name "$TABLE" --key "$KEY"
echo "OK"

echo "== 8. delete-table (drop) =="
aws_ddb delete-table --table-name "$TABLE" --query 'TableDescription.TableName' --output text
