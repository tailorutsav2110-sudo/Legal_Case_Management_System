from flask import Blueprint, render_template, request, redirect, session, url_for
from bson import ObjectId
from datetime import datetime
from helpers.notify import notify_admin, notify_lawyer, notify_client
from db import judgements, cases, users

judgement_bp = Blueprint("judgement", __name__)


# ====================== Case Judgement (admin) ======================
@judgement_bp.route("/judgement_cases")
def judgement_cases():
    if "user" not in session or session.get("role") != "admin":
        return redirect("/")

    all_cases = list(cases.find({}))
    all_lawyers = list(users.find({"role": "lawyer"}))

    for case in all_cases:
        case["lawyer_id"] = ObjectId(case["lawyer_id"])

        judgement = judgements.find_one({"case_id": case["_id"]})
        case["has_judgement"] = True if judgement else False

        if judgement:
            case["judgement_id"] = str(judgement["_id"])

    return render_template(
        "judgement/judgement_cases.html", cases=all_cases, lawyers=all_lawyers
    )


# ====================== Case Judgement (lawyer) ======================
@judgement_bp.route("/lawyer_judgement_cases")
def lawyer_judgement_cases():
    if "user_id" not in session or session.get("role") != "lawyer":
        return redirect("/")

    lawyer_id = session["user_id"]

    # sirf lawyer ke cases
    all_cases = list(cases.find({"lawyer_id": lawyer_id}))

    for case in all_cases:
        judgement = judgements.find_one({"case_id": case["_id"]})
        case["has_judgement"] = True if judgement else False

        if judgement:
            case["judgement_id"] = str(judgement["_id"])

    return render_template("judgement/lawyer_judgement_cases.html", cases=all_cases)


# ====================== Add Judgement ======================
@judgement_bp.route("/add_judgement/<case_id>", methods=["GET", "POST"])
def add_judgement(case_id):
    if "user" not in session or session.get("role") not in ["admin", "lawyer"]:
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        return "Case not found"

    if request.method == "POST":
        try:
            data = {
                "case_id": ObjectId(case_id),
                "case_title": case.get("title"),
                "judge_name": request.form.get("judge_name"),
                "judgement_date": datetime.strptime(
                    request.form.get("date"), "%Y-%m-%d"
                ),
                "decision": request.form.get("decision"),
                "description": request.form.get("description"),
                "status": "Final",
                "created_at": datetime.now(),
            }

            judgements.insert_one(data)

            # Update case status
            cases.update_one({"_id": ObjectId(case_id)}, {"$set": {"status": "Closed"}})

            # Roled based notifications
            client_user = users.find_one({"name": case.get("client"), "role": "client"})

            if client_user:
                notify_client(
                    client_user["_id"],
                    f"Judgement added for your case '{case.get('title')}' on {request.form.get('date')}\n(This Case Is Closed)",
                    )

            if session["role"] == "lawyer":
                notify_admin(
                    f"Lawyer {session['user']} added judgement for Case '{case.get('title')}'"
                )
            else:
                notify_lawyer(
                    case.get("lawyer_id"),
                    f"Admin added judgement for your Case '{case.get('title')}'",
                )

            return redirect(url_for("judgement.judgement_cases"))

        except Exception as e:
            return f"Error: {str(e)}"

    return render_template("judgement/add_judgement.html", case=case)


# ====================== View All Judgements ======================
@judgement_bp.route("/view_judgements")
def view_judgements():
    if "user_id" not in session:
        return redirect("/")

    all_judgements = list(judgements.find({}))

    for j in all_judgements:
        case = cases.find_one({"_id": j["case_id"]})
        j["case"] = case

    return render_template(
        "judgement/view_judgements.html",
        judgements=all_judgements,
        total_judgements=len(all_judgements),
    )


# ====================== View Single Judgement ======================
@judgement_bp.route("/view_judgement/<case_id>")
def view_judgement(case_id):
    if "user_id" not in session:
        return redirect("/")

    judgement = judgements.find_one({"case_id": ObjectId(case_id)})
    if not judgement:
        return "No judgement found"

    case = cases.find_one({"_id": ObjectId(case_id)})

    return render_template(
        "judgement/view_judgement.html", judgement=judgement, case=case
    )


# ====================== Delete Judgement ======================
@judgement_bp.route("/delete_judgement/<jid>")
def delete_judgement(jid):
    if "user" not in session or session.get("role") != "admin":
        return redirect("/")

    judgement = judgements.find_one({"_id": ObjectId(jid)})
    if not judgement:
        return "Judgement not found", 404

    case_id = judgement["case_id"]
    case = cases.find_one({"_id": case_id})

    # Roled based notifications
    client_user = users.find_one({"name": case.get("client"), "role": "client"})

    if client_user:
        notify_client(
            client_user["_id"],
            f"Judgement deleted for your case '{case.get('title')}' dated {judgement.get('judgement_date')}",
        )

    judgements.delete_one({"_id": ObjectId(jid)})

    if session["role"] == "lawyer":
        notify_admin(
            f"Lawyer {session['user']} deleted judgement for Case '{case.get('title')}'"
        )
    else:
        notify_lawyer(
            case.get("lawyer_id"),
            f"Admin deleted judgement for your Case '{case.get('title')}'",
        )

    cases.update_one({"_id": case_id}, {"$set": {"status": "Open"}})

    notify_lawyer(
        case.get("lawyer_id"),
        f"Admin deleted judgement for your Case '{case.get('title')}'",
    )

    return redirect(request.referrer)


# ====================== Mark Judgement as Final ======================
@judgement_bp.route("/mark_final/<jid>")
def mark_final(jid):
    if "user" not in session:
        return redirect("/")

    judgements.update_one({"_id": ObjectId(jid)}, {"$set": {"status": "Final"}})

    return redirect(request.referrer or url_for("judgement.view_judgements"))
