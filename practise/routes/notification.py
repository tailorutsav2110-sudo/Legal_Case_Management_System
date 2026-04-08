from flask import Blueprint, render_template, request, redirect, session
from bson import ObjectId
from db import notifications, users, cases

notification_bp = Blueprint("notification", __name__)


# ====================== Helper: Count Notifications ======================
def get_total_notifications():
    if "user_id" not in session:
        return 0

    user = users.find_one({"_id": ObjectId(session["user_id"])})
    if not user:
        return 0

    user_notifications = list(notifications.find({"user_id": user["_id"]}))
    return len(user_notifications)


# ====================== Send Notification (Admin/Lawyer) ======================
@notification_bp.route("/send_notification", methods=["GET", "POST"])
def send_notification():
    if "user_id" not in session or session["role"] not in ["admin", "lawyer"]:
        return redirect("/")

    role = session["role"]
    logged_in_user_id = session["user_id"]

    if request.method == "POST":
        selected_user_id = request.form.get("user_id")
        message = request.form.get("message")

        if not selected_user_id or not message:
            return "Missing data", 400

        selected_user = users.find_one({"_id": ObjectId(selected_user_id)})

        if not selected_user:
            return "User not found", 404

        if role == "lawyer":

            lawyer_cases = list(cases.find({"lawyer_id": str(logged_in_user_id)}))

            client_names = [
                c.get("client", "").strip().lower()
                for c in lawyer_cases
                if c.get("client")
            ]

            allowed_users = list(users.find({"role": "client"}))

            allowed_users = [
                u
                for u in allowed_users
                if u.get("name", "").strip().lower() in client_names
            ]

            allowed_user_ids = [str(u["_id"]) for u in allowed_users]

            if selected_user_id not in allowed_user_ids:
                return "Unauthorized - Not your client", 403

        notifications.insert_one(
            {"user_id": selected_user["_id"], "message": message, "status": "unread"}
        )

        return redirect("/admin_dashboard" if role == "admin" else "/dashboard")

    if role == "admin":
        all_users = list(users.find({}))

    elif role == "lawyer":
        lawyer_cases = list(cases.find({"lawyer_id": str(logged_in_user_id)}))

        client_names = list(
            set(
                [
                    c.get("client", "").strip().lower()
                    for c in lawyer_cases
                    if c.get("client")
                ]
            )
        )

        all_users = [
            u
            for u in users.find({"role": "client"})
            if u.get("name", "").strip().lower() in client_names
        ]

    else:
        all_users = []

    return render_template("notification_send.html", users=all_users, role=role)


# ====================== View Notifications (Client/Admin/Lawyer) ======================
@notification_bp.route("/view_notifications")
def view_notifications():
    if "user_id" not in session:
        return redirect("/")

    user = users.find_one({"_id": ObjectId(session["user_id"])})
    if not user:
        return "User not found. Please login again."

    role = user.get("role")

    # Same logic for ALL roles (admin, lawyer, client, staff)
    user_notifications = list(
        notifications.find({"user_id": user["_id"]}).sort("_id", -1)
    )

    total_notifications = len(user_notifications)

    unread_count = len([n for n in user_notifications if n.get("status") == "unread"])

    return render_template(
        "notifications.html",
        notifications=user_notifications,
        total_notifications=total_notifications,
        unread_count=unread_count,
        role=role,
    )


# ====================== Delete Notifications ======================
@notification_bp.route("/delete_notification/<nid>")
def delete_notification(nid):
    if "user_id" not in session:
        return redirect("/")

    notifications.delete_one({"_id": ObjectId(nid)})

    return redirect("/view_notifications")


# ====================== Mark as Read ======================
@notification_bp.route("/mark_read/<nid>")
def mark_read(nid):
    notifications.update_one({"_id": ObjectId(nid)}, {"$set": {"status": "read"}})
    return redirect("/view_notifications")


# ====================== for global unread_count ======================
@notification_bp.app_context_processor
def inject_notifications():
    if "user_id" not in session:
        return dict(notifications=[], unread_count=0)

    user_id = ObjectId(session["user_id"])

    user_notifications = list(notifications.find({"user_id": user_id}).sort("_id", -1))

    unread_count = len([n for n in user_notifications if n.get("status") == "unread"])

    return dict(notifications=user_notifications, unread_count=unread_count)
