"""Acces la DynamoDB (rulat local în LocalStack) prin boto3: catalog de note pentru studenți."""

import os
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
TABLE_NAME = os.getenv("TABLE_NAME", "Grades")


class DbError(Exception):
    """Eroare cu mesaj clar, afișabil direct utilizatorului."""


def get_client():
    return boto3.client(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        # Credențiale dummy: LocalStack acceptă orice valoare.
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        config=Config(connect_timeout=3, read_timeout=10, retries={"max_attempts": 1}),
    )


def _call(fn, condition_msg="Condiția nu a fost îndeplinită.", **kwargs):
    """Apelează boto3 și traduce erorile comune în mesaje clare."""
    try:
        return fn(**kwargs)
    except EndpointConnectionError:
        raise DbError(
            f"Nu mă pot conecta la {ENDPOINT_URL}. LocalStack rulează? "
            "Pornește-l cu: docker compose up -d"
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ResourceNotFoundException":
            raise DbError(f"Tabelul '{TABLE_NAME}' nu există. Creează-l cu: python -m app.cli init")
        if code == "ResourceInUseException":
            raise DbError(f"Tabelul '{TABLE_NAME}' există deja.")
        if code == "ConditionalCheckFailedException":
            raise DbError(condition_msg)
        raise DbError(f"Eroare DynamoDB ({code}): {e.response['Error'].get('Message', '')}")


def _validate_grade(grade):
    if not isinstance(grade, int) or isinstance(grade, bool) or not 1 <= grade <= 10:
        raise DbError(f"Notă invalidă: {grade!r}. Nota trebuie să fie un număr întreg între 1 și 10.")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key(student_id, course_id):
    return {"student_id": {"S": student_id}, "course_id": {"S": course_id}}


def _to_item(raw):
    """Convertește formatul DynamoDB ({'S': '...'} / {'N': '9'}) într-un dict simplu."""
    item = {}
    for k, v in raw.items():
        item[k] = int(v["N"]) if "N" in v else v["S"]
    return item


def create_table():
    client = get_client()
    _call(
        client.create_table,
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "student_id", "KeyType": "HASH"},  # partition key
            {"AttributeName": "course_id", "KeyType": "RANGE"},  # sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "student_id", "AttributeType": "S"},
            {"AttributeName": "course_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=TABLE_NAME, WaiterConfig={"Delay": 1, "MaxAttempts": 30})


def delete_table():
    client = get_client()
    _call(client.delete_table, TableName=TABLE_NAME)
    client.get_waiter("table_not_exists").wait(TableName=TABLE_NAME, WaiterConfig={"Delay": 1, "MaxAttempts": 30})


def add_grade(student_id, course_id, course_name, grade, semester):
    _validate_grade(grade)
    item = {
        "student_id": student_id,
        "course_id": course_id,
        "course_name": course_name,
        "grade": grade,
        "semester": semester,
        "updated_at": _now(),
    }
    _call(
        get_client().put_item,
        condition_msg=f"Nota pentru studentul '{student_id}' la cursul '{course_id}' există deja. "
        "Folosește comanda 'update' pentru a o modifica.",
        TableName=TABLE_NAME,
        Item={
            "student_id": {"S": student_id},
            "course_id": {"S": course_id},
            "course_name": {"S": course_name},
            "grade": {"N": str(grade)},
            "semester": {"S": semester},
            "updated_at": {"S": item["updated_at"]},
        },
        # Refuză duplicatele: scrie doar dacă nu există deja un item cu aceeași cheie.
        ConditionExpression="attribute_not_exists(student_id)",
    )
    return item


def get_grade(student_id, course_id):
    resp = _call(get_client().get_item, TableName=TABLE_NAME, Key=_key(student_id, course_id))
    return _to_item(resp["Item"]) if "Item" in resp else None


def list_grades(student_id):
    """Toate notele unui student, cu Query pe partition key (nu Scan). Sortate după course_id."""
    resp = _call(
        get_client().query,
        TableName=TABLE_NAME,
        KeyConditionExpression="student_id = :s",
        ExpressionAttributeValues={":s": {"S": student_id}},
    )
    return [_to_item(i) for i in resp["Items"]]


def average(grades):
    """Media notelor, calculată în Python (DynamoDB nu are funcții de agregare)."""
    if not grades:
        return None
    return round(sum(g["grade"] for g in grades) / len(grades), 2)


def update_grade(student_id, course_id, grade):
    _validate_grade(grade)
    resp = _call(
        get_client().update_item,
        condition_msg=f"Nu există nicio notă pentru studentul '{student_id}' la cursul '{course_id}'.",
        TableName=TABLE_NAME,
        Key=_key(student_id, course_id),
        UpdateExpression="SET grade = :g, updated_at = :u",
        ConditionExpression="attribute_exists(student_id)",
        ExpressionAttributeValues={":g": {"N": str(grade)}, ":u": {"S": _now()}},
        ReturnValues="ALL_NEW",
    )
    return _to_item(resp["Attributes"])


def delete_grade(student_id, course_id):
    _call(
        get_client().delete_item,
        condition_msg=f"Nu există nicio notă pentru studentul '{student_id}' la cursul '{course_id}'.",
        TableName=TABLE_NAME,
        Key=_key(student_id, course_id),
        ConditionExpression="attribute_exists(student_id)",
    )
