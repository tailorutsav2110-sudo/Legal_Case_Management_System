from flask import Blueprint, render_template, session, redirect, request, url_for
from bson.objectid import ObjectId
from db import cases, users, hearings, notifications, judgements
from helpers.notify import notify_admin
from datetime import datetime

client_bp = Blueprint("client", __name__)


# ================= Client Profile =================
@client_bp.route("/client/<id>")
def client_profile(id):
    if "user" not in session:
        return redirect("/")

    client = users.find_one({"_id": ObjectId(id), "role": "client"})

    if not client:
        return "Client not found"

    return render_template("profile/client_profile.html", client=client)


# ======================= Edit client profile =======================
@client_bp.route("/client/update/<id>", methods=["GET", "POST"])
def update_client_profile(id):
    if "user" not in session:
        return redirect("/")

    # Only allow self-update
    if session.get("user_id") != str(id):
        return "Unauthorized", 403

    client = users.find_one({"_id": ObjectId(id), "role": "client"})
    if not client:
        return "Client not found", 404

    if request.method == "POST":
        users.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "name": request.form.get("name"),
                    "phone": request.form.get("phone"),
                    "address": request.form.get("address"),
                }
            },
        )
        # notify_admin(f"Client {session['user']} updated their profile.")        # notify_admin

        return redirect(url_for("client.client_profile", id=id))

    return render_template("profile/update_client.html", client=client)


# ======================= Client show lawyer profile =======================
@client_bp.route("/my_lawyer/<case_id>")
def my_lawyer(case_id):
    if "user" not in session or session.get("role") != "client":
        return redirect("/")

    client_name = session["user"]
    case = cases.find_one({"_id": ObjectId(case_id), "client": client_name})

    if not case:
        return "Case not found or you do not have access", 403

    lawyer = users.find_one({"_id": ObjectId(case["lawyer_id"]), "role": "lawyer"})

    if not lawyer:
        return "Lawyer not assigned yet"

    return render_template("profile/lawyer_profile.html", lawyer=lawyer)


# ======================= Client Dashboard =======================
@client_bp.route("/client_dashboard")
def client_dashboard():
    if "user" not in session or session["role"] != "client":
        return redirect("/")

    client = users.find_one({"name": session["user"]})
    if not client:
        return "User not found"

    client_cases = list(cases.find({"client": client["name"]}))

    for case in client_cases:
        # Lawyer name
        if case.get("lawyer_id"):
            lawyer = users.find_one({"_id": ObjectId(case["lawyer_id"])})
            case["lawyer_name"] = lawyer["name"] if lawyer else "Not Found"
        else:
            case["lawyer_name"] = None

        # Judgement check
        judgement = judgements.find_one({"case_id": case["_id"]})
        case["has_judgement"] = True if judgement else False

        case_hearings = list(hearings.find({"case_id": str(case["_id"])}))

    upcoming_hearings = []
    for h in case_hearings:
        try:
            h_date = datetime.strptime(h["hearing_date"], "%Y-%m-%d")
            if h_date >= datetime.now():
                h["hearing_date_obj"] = h_date
                upcoming_hearings.append(h)
        except Exception as e:
            continue

    # Sort upcoming hearings by date
    if upcoming_hearings:
        upcoming_hearings.sort(key=lambda x: x["hearing_date_obj"])
        case["next_hearing"] = upcoming_hearings[0]
    else:
        case["next_hearing"] = None

    user_notifications = list(notifications.find({"user_id": client["_id"]}))
    unread_count = len([n for n in user_notifications if n["status"] == "unread"])

    return render_template(
        "client_dashboard.html",
        cases=client_cases,
        notifications=user_notifications,
        unread_count=unread_count,
    )


# ======================= Client View Single Case =======================
@client_bp.route("/client_case/<id>")
def client_case(id):
    if "user" not in session or session["role"] != "client":
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(id), "client": session["user"]})

    if not case:
        return "Access denied"

    lawyer_id = case.get("lawyer_id")
    try:
        if isinstance(lawyer_id, str):
            lawyer = users.find_one({"_id": ObjectId(lawyer_id)})
        else:
            lawyer = users.find_one({"_id": lawyer_id})
    except:
        lawyer = None

    case["lawyer_name"] = lawyer["name"] if lawyer else "Not Assigned"
    case_hearings = list(
        hearings.find({"case_id": str(case["_id"])}).sort("hearing_date", 1)
    )

    return render_template("client_case.html", case=case, hearings=case_hearings)


# ======================= All Cases =======================
@client_bp.route("/client/<client_id>/cases")
def all_cases(client_id):
    if "user" not in session or session["role"] != "client":
        return redirect("/")

    client = users.find_one({"_id": ObjectId(client_id)})
    if not client:
        return "User not found"

    client_cases = list(cases.find({"client": client["name"]}))
    for case in client_cases:
        case["_id"] = str(case["_id"])
        lawyer_id = case.get("lawyer_id")
        try:
            lawyer = users.find_one({"_id": ObjectId(lawyer_id)}) if lawyer_id else None
        except:
            lawyer = None
        case["lawyer_name"] = lawyer["name"] if lawyer else "Not Assigned"

    return render_template("client_cases.html", cases=client_cases)


# ======================= View Notifications =======================
@client_bp.route("/client/<client_id>/notifications")
def view_notifications(client_id):
    if "user" not in session or session["role"] != "client":
        return redirect("/")

    client = users.find_one({"_id": ObjectId(client_id)})
    if not client:
        return "User not found"

    client_notifications = list(notifications.find({"user_id": client["_id"]}))
    unread_count = notifications.count_documents(
        {"user_id": client["_id"], "status": "unread"}
    )

    return render_template(
        "client_notifications.html",
        notifications=client_notifications,
        unread_count=unread_count,
    )


# ======================= Client View Hearings =======================
@client_bp.route("/client_case/<case_id>/hearings")
def client_case_hearings(case_id):
    if "user" not in session or session["role"] != "client":
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(case_id), "client": session["user"]})

    if not case:
        return "Access Denied"

    case_hearings = list(
        hearings.find({"case_id": str(case["_id"])}).sort("hearing_date", 1)
    )

    lawyer_id = case.get("lawyer_id")
    try:
        if isinstance(lawyer_id, str):
            lawyer = users.find_one({"_id": ObjectId(lawyer_id)})
        else:
            lawyer = users.find_one({"_id": lawyer_id})
    except:
        lawyer = None
    case["lawyer_name"] = lawyer["name"] if lawyer else "Not Assigned"

    return render_template(
        "client_case_hearings.html", case=case, hearings=case_hearings
    )
