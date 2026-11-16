"""Acces la DynamoDB (rulat local în LocalStack) prin boto3: funcții CRUD pentru tabelul Tasks."""

import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
TABLE_NAME = os.getenv("TABLE_NAME", "Tasks")


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


def _call(fn, **kwargs):
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
            raise DbError("Task-ul nu există.")
        raise DbError(f"Eroare DynamoDB ({code}): {e.response['Error'].get('Message', '')}")


def _to_item(raw):
    """Convertește formatul DynamoDB ({'S': '...'}) într-un dict simplu."""
    return {k: v["S"] for k, v in raw.items()}


def create_table():
    client = get_client()
    _call(
        client.create_table,
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},   # partition key
            {"AttributeName": "task_id", "KeyType": "RANGE"},  # sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "task_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=TABLE_NAME, WaiterConfig={"Delay": 1, "MaxAttempts": 30})


def delete_table():
    client = get_client()
    _call(client.delete_table, TableName=TABLE_NAME)
    client.get_waiter("table_not_exists").wait(TableName=TABLE_NAME, WaiterConfig={"Delay": 1, "MaxAttempts": 30})


def add_task(user_id, title):
    item = {
        "user_id": user_id,
        "task_id": uuid.uuid4().hex[:8],
        "title": title,
        "status": "todo",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _call(
        get_client().put_item,
        TableName=TABLE_NAME,
        Item={k: {"S": v} for k, v in item.items()},
    )
    return item


def get_task(user_id, task_id):
    resp = _call(
        get_client().get_item,
        TableName=TABLE_NAME,
        Key={"user_id": {"S": user_id}, "task_id": {"S": task_id}},
    )
    return _to_item(resp["Item"]) if "Item" in resp else None


def list_tasks(user_id):
    """Toate task-urile unui user, cu Query pe partition key (nu Scan)."""
    resp = _call(
        get_client().query,
        TableName=TABLE_NAME,
        KeyConditionExpression="user_id = :u",
        ExpressionAttributeValues={":u": {"S": user_id}},
    )
    return sorted((_to_item(i) for i in resp["Items"]), key=lambda t: t["created_at"])


def complete_task(user_id, task_id):
    resp = _call(
        get_client().update_item,
        TableName=TABLE_NAME,
        Key={"user_id": {"S": user_id}, "task_id": {"S": task_id}},
        UpdateExpression="SET #s = :done",
        ConditionExpression="attribute_exists(task_id)",
        ExpressionAttributeNames={"#s": "status"},  # "status" e cuvânt rezervat în DynamoDB
        ExpressionAttributeValues={":done": {"S": "done"}},
        ReturnValues="ALL_NEW",
    )
    return _to_item(resp["Attributes"])


def delete_task(user_id, task_id):
    _call(
        get_client().delete_item,
        TableName=TABLE_NAME,
        Key={"user_id": {"S": user_id}, "task_id": {"S": task_id}},
        ConditionExpression="attribute_exists(task_id)",
    )
