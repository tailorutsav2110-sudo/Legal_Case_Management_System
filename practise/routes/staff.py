from flask import Blueprint, render_template, session, redirect, url_for, request
from datetime import datetime
from bson import ObjectId
from db import cases, users, hearings, documents, judgements

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


# ======================= Role Check Function =======================
def is_staff():
    return session.get("role") == "staff"


def check_staff():
    if "user" not in session or not is_staff():
        return False
    return True


# ================= Staff Profile =================
@staff_bp.route("/profile/<id>")
def staff_profile(id):
    if "user" not in session:
        return redirect("/")

    staff = users.find_one({"_id": ObjectId(id), "role": "staff"})

    if not staff:
        return "Staff not found"

    return render_template("profile/staff_profile.html", staff=staff)


# ================= Update Staff Profile =================
@staff_bp.route("/profile/update/<id>", methods=["GET", "POST"])
def update_staff_profile(id):
    if "user" not in session:
        return redirect("/")

    if session.get("user_id") != str(id):
        return "Unauthorized", 403

    staff = users.find_one({"_id": ObjectId(id), "role": "staff"})
    if not staff:
        return "Staff not found", 404

    if request.method == "POST":
        users.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "email": request.form.get("email"),
                    "phone": request.form.get("phone"),
                }
            },
        )

        return redirect(url_for("staff.staff_profile", id=id))

    return render_template("profile/update_staff.html", staff=staff)


# ======================= Dashboard =======================
@staff_bp.route("/dashboard")
def dashboard():
    if not check_staff():
        return "Unauthorized", 403

    total_cases = cases.count_documents({})
    total_users = users.count_documents({})
    total_hearings = hearings.count_documents({})
    total_documents = documents.count_documents({})

    return render_template(
        "staff/staff_dashboard.html",
        total_cases=total_cases,
        total_users=total_users,
        total_hearings=total_hearings,
        total_documents=total_documents,
    )


# ======================= View All Cases =======================
@staff_bp.route("/cases")
def view_cases():
    if not check_staff():
        return "Unauthorized", 403

    all_cases = list(cases.find())

    for c in all_cases:
        c["_id"] = str(c["_id"])

        # Get Lawyer Name
        lawyer = users.find_one({"_id": ObjectId(c["lawyer_id"])})
        c["lawyer_name"] = lawyer["name"] if lawyer else "N/A"

    return render_template("staff/staff_case.html", cases=all_cases)


# ======================= View All Hearings =======================
@staff_bp.route("/hearings")
def view_hearings():
    if not check_staff():
        return "Unauthorized", 403

    all_hearings = list(hearings.find())

    for h in all_hearings:
        h["_id"] = str(h["_id"])
        h["case_id"] = str(h["case_id"])
        h["lawyer_id"] = str(h["lawyer_id"])

        h["case_id_short"] = h["case_id"][:5]
        h["lawyer_id_short"] = h["lawyer_id"][:5]

    return render_template("staff/staff_hearing.html", hearings=all_hearings)


# ======================= View Documents =======================
@staff_bp.route("/documents")
def view_documents():
    if not check_staff():
        return "Unauthorized", 403

    all_docs = list(documents.find())

    for d in all_docs:
        d["_id"] = str(d["_id"])
        d["case_id"] = str(d["case_id"])

    return render_template("staff/staff_document.html", documents=all_docs)


# ======================= View Users =======================
@staff_bp.route("/users")
def view_users():
    if not check_staff():
        return "Unauthorized", 403

    all_users = list(users.find())

    for u in all_users:
        u["_id"] = str(u["_id"])

    return render_template("staff/staff_users.html", users=all_users)


# ======================= View Judgements =======================
@staff_bp.route("/judgements")
def view_judgements():
    if not check_staff():
        return "Unauthorized", 403

    all_judgements = list(judgements.find())

    for j in all_judgements:
        j["_id"] = str(j["_id"])
        j["case_id"] = str(j["case_id"])
        j["case_id_short"] = j["case_id"][:5]

    return render_template("staff/staff_judgements.html", judgements=all_judgements)


# ======================= Block Any Edit/Delete Access =======================
@staff_bp.app_errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403
