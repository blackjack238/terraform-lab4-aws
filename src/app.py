import json
import boto3
import os
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME")
AUDIT_BUCKET = os.environ.get("AUDIT_BUCKET")

if not TABLE_NAME:
    raise ValueError("Environment variable TABLE_NAME is not set.")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

s3 = boto3.client("s3")
comprehend = boto3.client("comprehend")


def json_response(status_code: int, body) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def write_audit_log(action: str, payload: dict) -> None:
    if not AUDIT_BUCKET:
        return

    timestamp = datetime.utcnow().isoformat()
    log_key = f"audit/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4()}.json"

    log_data = {
        "timestamp": timestamp,
        "action": action,
        "payload": payload,
    }

    s3.put_object(
        Bucket=AUDIT_BUCKET,
        Key=log_key,
        Body=json.dumps(log_data, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def get_http_method(event: dict) -> str:
    if "httpMethod" in event:
        return event["httpMethod"]

    return event.get("requestContext", {}).get("http", {}).get("method", "")


def get_path_parameters(event: dict) -> dict:
    return event.get("pathParameters") or {}


def get_query_parameters(event: dict) -> dict:
    return event.get("queryStringParameters") or {}


def parse_body(event: dict) -> dict:
    body = event.get("body")
    if not body:
        return {}

    if isinstance(body, dict):
        return body

    return json.loads(body)


def get_raw_path(event: dict) -> str:
    return event.get("rawPath", "")


def create_task(body: dict) -> dict:
    title = body.get("title")
    description = body.get("description", "")
    priority = body.get("priority", "medium")
    status = body.get("status", "open")

    if not title:
        return json_response(400, {"message": "Field 'title' is required."})

    if status not in {"open", "in_progress", "done"}:
        return json_response(400, {"message": "Invalid status value."})

    if priority not in {"low", "medium", "high"}:
        return json_response(400, {"message": "Invalid priority value."})

    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    item = {
        "id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "ai_sentiment": None,
        "ai_sentiment_score": None,
    }

    table.put_item(Item=item)
    write_audit_log("CREATE_TASK", item)

    return json_response(
        201,
        {
            "message": "Task created",
            "task": item,
        },
    )


def get_tasks(query_params: dict) -> dict:
    status_filter = query_params.get("status")

    if status_filter:
        response = table.query(
            IndexName="status-index",
            KeyConditionExpression="#s = :status_value",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":status_value": status_filter},
        )
        items = response.get("Items", [])
    else:
        response = table.scan()
        items = response.get("Items", [])

    result = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "priority": item.get("priority"),
            "status": item.get("status"),
            "ai_sentiment": item.get("ai_sentiment"),
        }
        for item in items
    ]

    return json_response(200, result)


def update_task(task_id: str, body: dict) -> dict:
    new_status = body.get("status")

    if not new_status:
        return json_response(400, {"message": "Field 'status' is required."})

    if new_status not in {"open", "in_progress", "done"}:
        return json_response(400, {"message": "Invalid status value."})

    now = datetime.utcnow().isoformat()

    try:
        response = table.update_item(
            Key={"id": task_id},
            UpdateExpression="SET #s = :status, updated_at = :updated_at",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": new_status,
                ":updated_at": now,
            },
            ConditionExpression="attribute_exists(id)",
            ReturnValues="ALL_NEW",
        )

        updated_item = response.get("Attributes", {})
        write_audit_log("UPDATE_TASK_STATUS", updated_item)

        return json_response(
            200,
            {
                "message": "Task updated",
                "task": updated_item,
            },
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return json_response(404, {"message": "Task not found."})

        raise


def prioritize_task(task_id: str) -> dict:
    response = table.get_item(Key={"id": task_id})
    item = response.get("Item")

    if not item:
        return json_response(404, {"message": "Task not found."})

    description = (item.get("description") or "").strip()

    if not description:
        return json_response(400, {"message": "Task description is empty."})

    sentiment_response = comprehend.detect_sentiment(
        Text=description[:500],
        LanguageCode="en"
    )

    sentiment = sentiment_response.get("Sentiment")
    sentiment_score = sentiment_response.get("SentimentScore", {})

    current_priority = item.get("priority", "medium")

    if sentiment == "NEGATIVE":
        new_priority = "high"
    elif sentiment == "POSITIVE" and current_priority == "low":
        new_priority = "low"
    else:
        new_priority = current_priority

    now = datetime.utcnow().isoformat()

    try:
        update_response = table.update_item(
            Key={"id": task_id},
            UpdateExpression="""
                SET priority = :priority,
                    ai_sentiment = :ai_sentiment,
                    ai_sentiment_score = :ai_sentiment_score,
                    updated_at = :updated_at
            """,
            ExpressionAttributeValues={
                ":priority": new_priority,
                ":ai_sentiment": sentiment,
                ":ai_sentiment_score": {
                    "Positive": str(sentiment_score.get("Positive", 0)),
                    "Negative": str(sentiment_score.get("Negative", 0)),
                    "Neutral": str(sentiment_score.get("Neutral", 0)),
                    "Mixed": str(sentiment_score.get("Mixed", 0)),
                },
                ":updated_at": now,
            },
            ConditionExpression="attribute_exists(id)",
            ReturnValues="ALL_NEW",
        )

        updated_item = update_response.get("Attributes", {})
        write_audit_log("PRIORITIZE_TASK", updated_item)

        return json_response(
            200,
            {
                "message": "Task prioritized",
                "task": updated_item,
                "ai_analysis": {
                    "sentiment": sentiment,
                    "sentiment_score": sentiment_score,
                },
            },
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return json_response(404, {"message": "Task not found."})

        raise


def handler(event, context):
    try:
        http_method = get_http_method(event)
        path_params = get_path_parameters(event)
        query_params = get_query_parameters(event)
        body = parse_body(event)
        raw_path = get_raw_path(event)

        if http_method == "POST" and raw_path == "/tasks":
            return create_task(body)

        if http_method == "GET" and raw_path == "/tasks":
            return get_tasks(query_params)

        if http_method == "PUT":
            task_id = path_params.get("id")
            if not task_id:
                return json_response(400, {"message": "Task ID is required in path."})

            return update_task(task_id, body)

        if http_method == "POST" and raw_path.endswith("/prioritize"):
            task_id = path_params.get("id")
            if not task_id:
                return json_response(400, {"message": "Task ID is required in path."})

            return prioritize_task(task_id)

        return json_response(405, {"message": "Method Not Allowed"})

    except json.JSONDecodeError:
        return json_response(400, {"message": "Invalid JSON in request body."})

    except Exception as e:
        print(f"Error: {str(e)}")
        return json_response(500, {"message": "Internal Server Error"})