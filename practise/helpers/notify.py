from datetime import datetime
from bson import ObjectId
from db import notifications, users


def notify_admin(message):
    admins = list(users.find({"role": "admin"}))

    for admin in admins:
        notifications.insert_one(
            {
                "user_id": admin["_id"],
                "message": message,
                "role": "admin",
                "status": "unread",
                "created_at": datetime.utcnow(),
            }
        )


def notify_lawyer(lawyer_id, message):
    notifications.insert_one(
        {
            "user_id": ObjectId(lawyer_id),
            "message": message,
            "role": "lawyer",
            "status": "unread",
            "created_at": datetime.utcnow(),
        }
    )


def notify_client(client_id, message):
    notifications.insert_one(
        {
            "user_id": ObjectId(client_id),
            "message": message,
            "role": "client",
            "status": "unread",
            "created_at": datetime.utcnow(),
        }
    )


def notify_judgement(case):
    # Client
    if case.get("client_id"):
        notifications.insert_one(
            {
                "user_id": ObjectId(case["client_id"]),
                "message": f"Judgement added for your case: {case['title']}",
                "role": "client",
                "status": "unread",
                "created_at": datetime.utcnow(),
            }
        )

    # Lawyer
    if case.get("lawyer_id"):
        notifications.insert_one(
            {
                "user_id": ObjectId(case["lawyer_id"]),
                "message": f"Judgement added for case: {case['title']}",
                "role": "lawyer",
                "status": "unread",
                "created_at": datetime.utcnow(),
            }
        )
