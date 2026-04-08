from flask import Blueprint, render_template, request, redirect, session, url_for
from bson.objectid import ObjectId
from db import users, cases, hearings, documents, notifications
from helpers.notify import notify_lawyer

admin_bp = Blueprint("admin", __name__)

# ================= Lawyer Profile =================
@admin_bp.route("/admin/<id>")
def admin_profile(id):
    if "user" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/")

    admin = users.find_one({
        "_id": ObjectId(id),
        "role": "admin"
    })

    if not admin:
        return "Admin not found"

    return render_template("profile/admin_profile.html", admin=admin)

# ======================= Edit admin profile =======================
@admin_bp.route("/admin/update/<id>", methods=["GET", "POST"])
def update_admin_profile(id):
    if "user" not in session:
        return redirect("/")

    # Only allow self-update
    if session.get("user_id") != str(id):
        return "Unauthorized", 403

    if session.get("role") != "admin":
        return "Unauthorized", 403

    admin = users.find_one({"_id": ObjectId(id), "role": "admin"})
    if not admin:
        return "Admin not found", 404

    if request.method == "POST":
        users.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "name": request.form.get("name"),
                "phone": request.form.get("phone")
            }}
        )
        return redirect(url_for("admin.admin_profile", id=id))

    return render_template("profile/update_admin.html", admin=admin)

# ======================= Admin Dashboard =======================
@admin_bp.route("/admin_dashboard")
def admin_dashboard():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    total_users = users.count_documents({})
    total_cases = cases.count_documents({})
    total_hearings = hearings.count_documents({})
    total_documents = documents.count_documents({})

    unread_notifications = list(
        notifications.find({
            "user_id": ObjectId(session["user_id"]),
            "status": "unread"
        }).sort("created_at", -1)
    )

    unread_count = len(unread_notifications)

    all_notifications = list(
        notifications.find({
            "user_id": ObjectId(session["user_id"])
        }).sort("created_at", -1)
    )

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_cases=total_cases,
        total_hearings=total_hearings,
        total_documents=total_documents,
        unread_count=unread_count,
        notifications=unread_notifications,   
        all_notifications=all_notifications  
    )


# ======================= View All Users =======================
@admin_bp.route("/admin/users")
def admin_users():  
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    all_users = list(users.find({}, {"password": 0}))
    for user in all_users:
        user["_id"] = str(user["_id"])

    return render_template("admin_users.html", users=all_users)

# ======================= Edit User =======================
@admin_bp.route("/admin/edit_user/<id>", methods=["GET", "POST"])
def admin_edit_user(id):
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    user = users.find_one({"_id": ObjectId(id)})
    if not user:
        return "User not found"

    if request.method == "POST":
        users.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "name": request.form["name"],
                "email": request.form["email"],
                "role": request.form["role"]
            }}
        )
        return redirect("/admin/users")

    return render_template("edit_user.html", user=user)

# ======================= Delete User =======================
@admin_bp.route("/delete_user/<id>")
def admin_delete_user(id):
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    users.delete_one({"_id": ObjectId(id)})
    return redirect("/admin/users")

# =======================search user=======================
@admin_bp.route("/search_user")
def search_user():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    name_query = request.args.get("name")

    if not name_query:
        return redirect("/admin/users")

    query = {
        "$or": [
            {"name": {"$regex": name_query, "$options": "i"}},
            {"role": {"$regex": name_query, "$options": "i"}},
        ]
    }

    users_list = list(users.find(query))

    if not users_list:
        return render_template("search_user.html",users=[],error=f"No user found matching '{name_query}'")

    return render_template("search_user.html", users=users_list)

# ======================= View All Cases =======================
@admin_bp.route("/admin/cases")
def admin_cases():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    all_cases = list(cases.find())
    for case in all_cases:
        case["_id"] = str(case["_id"])
        case["lawyer_id"] = str(case.get("lawyer_id", ""))

    lawyers = list(users.find({"role": "lawyer"}))
    for lawyer in lawyers:
        lawyer["_id"] = str(lawyer["_id"])

    return render_template("admin_cases.html",cases=all_cases,lawyers=lawyers)

# ======================= Edit Case =======================
@admin_bp.route("/admin/edit_case/<id>", methods=["GET", "POST"])
def admin_edit_case(id):
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(id)})
    if not case:
        return "Case not found"

    if request.method == "POST":
        cases.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "title": request.form["title"],
                "description": request.form["description"],
                "status": request.form["status"]
            }}
        )

        lawyer_id = case.get("lawyer_id")
        if lawyer_id:
            notify_lawyer(lawyer_id,f"Case '{request.form["title"]}' has been updated by admin.")

        return redirect("/admin/cases")

    return render_template("edit_case.html", case=case)

# ======================= Delete Case =======================
@admin_bp.route("/delete_case/<id>")
def admin_delete_case(id):
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    cases.delete_one({"_id": ObjectId(id)})
    return redirect("/admin/cases")
