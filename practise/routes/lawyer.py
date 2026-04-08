from flask import Blueprint, render_template, request, redirect, session, url_for
from db import cases, users, hearings, notifications
from bson.objectid import ObjectId
from helpers.notify import notify_admin

cases_bp = Blueprint("cases", __name__)


# ================= Lawyer Profile =================
@cases_bp.route("/lawyer/<id>")
def lawyer_profile(id):
    if "user" not in session:
        return redirect("/")

    lawyer = users.find_one({"_id": ObjectId(id), "role": "lawyer"})

    if not lawyer:
        return "Lawyer not found"

    return render_template("profile/lawyer_profile.html", lawyer=lawyer)


# =======================Edit lawyer profile=======================
@cases_bp.route("/lawyer/update/<id>", methods=["GET", "POST"])
def update_lawyer_profile(id):
    if "user" not in session:
        return redirect("/")

    # Only allow self-update
    if session.get("user_id") != str(id):
        return "Unauthorized", 403

    lawyer = users.find_one({"_id": ObjectId(id), "role": "lawyer"})
    if not lawyer:
        return "Lawyer not found", 404

    if request.method == "POST":
        users.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "name": request.form.get("name"),
                    "phone": request.form.get("phone"),
                    "experience": request.form.get("experience"),
                    "specialization": request.form.get("specialization"),
                    "bio": request.form.get("bio"),
                }
            },
        )

        return redirect(url_for("cases.lawyer_profile", id=id))

    return render_template("profile/update_lawyer.html", lawyer=lawyer)


# ======================= Lawyer show client profile =======================
@cases_bp.route("/my_client/<case_id>")
def my_client(case_id):
    if "user" not in session or session.get("role") != "lawyer":
        return redirect("/")

    lawyer_id = session["user_id"]

    # Find the case assigned to this lawyer
    case = cases.find_one({"_id": ObjectId(case_id), "lawyer_id": lawyer_id})

    if not case:
        return "Case not found or you do not have access", 403

    # Get the client assigned to this case
    client = users.find_one({"name": case["client"], "role": "client"})

    if not client:
        return "Client not found"

    return render_template("profile/client_profile.html", client=client)


# =======================dashboard details=======================
@cases_bp.route("/dashboard")
def dashboard():
    # Only lawyer can access
    if "user" not in session or session["role"] != "lawyer":
        return redirect("/")

    lawyer = users.find_one({"_id": ObjectId(session["user_id"])})
    if not lawyer:
        return redirect("/")

    unread_count = notifications.count_documents(
        {"user_id": lawyer["_id"], "status": "unread"}
    )

    all_notifications = list(
        notifications.find({"user_id": lawyer["_id"]}).sort("created_at", -1)
    )

    total_cases = cases.count_documents({"lawyer_id": lawyer["_id"]})
    total_hearings = hearings.count_documents({"lawyer_id": lawyer["_id"]})

    return render_template(
        "dashboard.html",
        unread_count=unread_count,
        notifications=all_notifications,
        total_cases=total_cases,
        total_hearings=total_hearings,
    )


# =======================View cases=======================
@cases_bp.route("/cases")
def view_cases():
    if "user" not in session:
        return redirect("/")

    if session["role"] == "lawyer":
        data = list(cases.find({"lawyer_id": session["user_id"]}))
    else:
        data = list(cases.find())

    for case in data:
        case["_id"] = str(case["_id"])
        case["lawyer_id"] = str(case["lawyer_id"])

    lawyers = list(users.find({"role": "lawyer"}))
    for lawyer in lawyers:
        lawyer["_id"] = str(lawyer["_id"])

    return render_template("cases.html", cases=data, lawyers=lawyers)


# =======================Add cases(admin,lawyer)=======================
@cases_bp.route("/add_case", methods=["GET", "POST"])
def add_case():
    if session.get("role") not in ["admin", "lawyer"]:
        return "Access denied"

    if request.method == "POST":
        form_data = request.form.to_dict()

        cases.insert_one(
            {
                "title": form_data.get("title"),
                "client": form_data.get("client"),
                "description": form_data.get("description"),
                "status": form_data.get("status"),
                "lawyer_id": form_data.get("lawyer_id"),
            }
        )

        notify_admin(
            f"lawyer/admin {session['user']} created a new case: {form_data.get('title')}"
        )  # notify_admin

        if session["role"] == "admin":
            return redirect("/admin/cases")
        else:
            return redirect("/cases")

    lawyers = list(users.find({"role": "lawyer"}))
    return render_template("add_case.html", lawyers=lawyers)


# =======================Edit cases=======================
@cases_bp.route("/edit_case/<id>", methods=["GET", "POST"])
def edit_case(id):
    if "user" not in session:
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(id)})
    if not case:
        return "Case not found"

    if session["role"] == "lawyer" and case["lawyer_id"] != session["user_id"]:
        return "Access Denied"

    if session["role"] not in ["lawyer", "admin"]:
        return "Access Denied"

    if request.method == "POST":
        cases.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "title": request.form["title"],
                    "description": request.form["description"],
                    "status": request.form["status"],
                }
            },
        )

        notify_admin(
            f"lawyer/admin {session['user']} Updated case Id {id}"
        )  # notify_admin

        if session["role"] == "admin":
            return redirect("/admin/cases")
        return redirect("/cases")

    return render_template("edit_case.html", case=case)


# =======================delete cases=======================
@cases_bp.route("/delete_case/<id>")
def delete_case(id):
    if "user" not in session:
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(id)})
    if session["role"] == "lawyer" and case["lawyer_id"] != session["user_id"]:
        return "Access Denied"

    notify_admin(f"Lawyer {session['user']} Deleted case id {id}")  # notify_admin

    cases.delete_one({"_id": ObjectId(id)})
    return redirect("/cases")


# =======================search case=======================
@cases_bp.route("/search_case")
def search_case():
    if "user" not in session or session["role"] not in ["admin", "lawyer"]:
        return redirect("/")

    search_query = request.args.get("title")
    if not search_query:
        return redirect("/admin/cases" if session["role"] == "admin" else "/cases")

    if session["role"] == "lawyer":
        query = {
            "title": {"$regex": search_query, "$options": "i"},
            "lawyer_id": session["user_id"],
        }

    else:
        query = {
            "$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"client": {"$regex": search_query, "$options": "i"}},
                {"status": {"$regex": search_query, "$options": "i"}},
            ]
        }

    case = cases.find_one(query)

    if not case:
        return render_template(
            "search_case.html", error=f"No case found matching '{search_query}'"
        )

    lawyer = users.find_one({"_id": ObjectId(case["lawyer_id"])})
    case["lawyer_name"] = lawyer["name"] if lawyer else "Not Assigned"

    return render_template("search_case.html", case=case)
