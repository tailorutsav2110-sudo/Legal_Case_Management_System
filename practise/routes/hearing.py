from flask import Blueprint, render_template, request, redirect, url_for, session
from bson import ObjectId
from db import cases, users, hearings, notifications
from helpers.notify import notify_admin, notify_lawyer, notify_client
from datetime import datetime

hearing_bp = Blueprint("hearing", __name__)


# ======================= add hearing =======================
@hearing_bp.route("/add_hearing/<case_id>", methods=["GET", "POST"])
def add_hearing(case_id):
    if "user" not in session or session["role"] not in ["lawyer", "admin"]:
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        return "Case not found"

    if session["role"] == "lawyer":
        if str(case.get("lawyer_id")) != session["user_id"]:
            return "Access Denied"

    lawyer_options = []
    if session["role"] == "admin":
        if case.get("lawyer_id"):
            lawyer_data = users.find_one(
                {"_id": ObjectId(case["lawyer_id"]), "role": "lawyer"}
            )
            if lawyer_data:
                lawyer_options.append(
                    {
                        "id": str(lawyer_data["_id"]),
                        "name": lawyer_data.get("name", "Unnamed"),
                    }
                )

    if request.method == "POST":
        selected_lawyer_id = (
            request.form.get("lawyer_id")
            if session["role"] == "admin"
            else session["user_id"]
        )

        hearing_data = {
            "case_id": case_id,
            "lawyer_id": selected_lawyer_id,
            "hearing_date": request.form["hearing_date"],
            "hearing_time": request.form["hearing_time"],
            "judge_name": request.form["judge_name"],
            "court_room": request.form["court_room"],
            "remarks": request.form["remarks"],
        }

        hearings.insert_one(hearing_data)

        # Role-Based Notification
        client_name = case.get("client")
        client_user = users.find_one({"name": client_name, "role": "client"})

        if client_user:
            notify_client(
                client_user["_id"],
                f"New hearing scheduled for your case '{case.get('title')}' on {request.form['hearing_date']} at {request.form['hearing_time']}",
            )

        if session["role"] == "lawyer":
            notify_admin(
                f"Lawyer {session['user']} added a new hearing for Case '{case.get('title')}' on {request.form['hearing_date']}"
            )
        else:
            notify_lawyer(
                selected_lawyer_id,
                f"Admin scheduled a new hearing for your Case '{case.get('title')}' on {request.form['hearing_date']} at {request.form['hearing_time']}",
            )

        return redirect(url_for("hearing.view_hearing", case_id=case_id))

    return render_template("add_hearing.html", case=case, lawyer_options=lawyer_options)


# ======================= view hearing =======================
@hearing_bp.route("/hearings/<case_id>")
def view_hearing(case_id):
    if "user" not in session:
        return redirect("/")

    case = cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        return "Case not found"

    if session["role"] == "lawyer":
        if str(case.get("lawyer_id")) != session["user_id"]:
            return "Access Denied"

    data = list(hearings.find({"case_id": case_id}).sort("hearing_date", 1))

    today = datetime.today().date()

    for h in data:
        # exact match format
        h_date = datetime.strptime(h["hearing_date"], "%Y-%m-%d").date()

        if h_date >= today:
            h["is_upcoming"] = True
        else:
            h["is_upcoming"] = False

        h["case_title"] = case.get("title", "N/A")

    return render_template("view_hearing.html", hearings=data)


# ======================= update hearing =======================
@hearing_bp.route("/update_hearing/<hearing_id>", methods=["GET", "POST"])
def update_hearing(hearing_id):
    if "user" not in session or session["role"] not in ["lawyer", "admin"]:
        return redirect("/")

    hearing = hearings.find_one({"_id": ObjectId(hearing_id)})
    if not hearing:
        return "Hearing not found"

    case = cases.find_one({"_id": ObjectId(hearing["case_id"])})

    if request.method == "POST":
        updated_data = {
            "hearing_date": request.form["hearing_date"],
            "hearing_time": request.form["hearing_time"],
            "judge_name": request.form["judge_name"],
            "court_room": request.form["court_room"],
            "remarks": request.form["remarks"],
        }

        hearings.update_one({"_id": ObjectId(hearing_id)}, {"$set": updated_data})

        # Role Based notifications
        client_user = users.find_one({"name": case.get("client"), "role": "client"})

        if client_user:
            notify_client(
                client_user["_id"],
                f"Hearing UPDATED for your case '{case.get('title')}' on {updated_data['hearing_date']} at {updated_data['hearing_time']}",
            )

        if session["role"] == "lawyer":
            notify_admin(f"Hearing updated for Case '{case.get('title')}'")
        else:
            notify_lawyer(
                hearing["lawyer_id"],
                f"Admin updated hearing for your Case '{case.get('title')}'",
            )

        return redirect(url_for("hearing.admin_hearings"))

    return render_template("update_hearing.html", hearing=hearing)


# =======================delete hearing=======================
@hearing_bp.route("/delete_hearing/<hearing_id>/<case_id>")
def delete_hearing(hearing_id, case_id):
    if "user" not in session or session["role"] not in ["lawyer", "admin"]:
        return redirect("/")

    hearing = hearings.find_one({"_id": ObjectId(hearing_id)})
    if not hearing:
        return "Hearing not found"

    case = cases.find_one({"_id": ObjectId(case_id)})

    # Role Based notifications
    client_user = users.find_one({"name": case.get("client"), "role": "client"})

    if client_user:
        notify_client(
            client_user["_id"],
            f"Hearing Canceled for your case '{case.get('title')}' which was on {hearing.get('hearing_date')} at {hearing.get('hearing_time')}",
        )

    hearings.delete_one({"_id": ObjectId(hearing_id)})

    if session["role"] == "lawyer":
        notify_admin(f"Hearing Canceled for Case '{case.get('title')}'")
    else:
        notify_lawyer(
            hearing["lawyer_id"],
            f"Admin Canceled hearing for your Case '{case.get('title')}'",
        )

    return redirect(url_for("hearing.admin_hearings", case_id=case_id))


# =======================lawyer view own all hearing=======================
@hearing_bp.route("/view_hearings")
def all_hearings():
    if "user" not in session:
        return redirect("/")

    if session["role"] == "lawyer":
        data = list(hearings.find({"lawyer_id": session["user_id"]}))
    else:
        data = list(hearings.find())

    today = datetime.today().date()

    for h in data:
        h["_id"] = str(h["_id"])

        case = cases.find_one({"_id": ObjectId(h["case_id"])})
        h["case_title"] = case["title"] if case else "N/A"

        # only upcoming logic
        h_date = datetime.strptime(h["hearing_date"], "%Y-%m-%d").date()
        h["is_upcoming"] = h_date >= today

    return render_template("view_hearing.html", hearings=data)


# =======================admin view all hearings=======================
@hearing_bp.route("/admin/hearings")
def admin_hearings():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    all_hearings = list(hearings.find().sort("hearing_date", 1))

    today = datetime.today().date()
    enriched_hearings = []

    for h in all_hearings:
        h["_id"] = str(h["_id"])

        case_title = "N/A"
        if "case_id" in h and len(h["case_id"]) == 24:
            try:
                case = cases.find_one({"_id": ObjectId(h["case_id"])})
                if case:
                    case_title = case.get("title", "N/A")
            except:
                pass

        lawyer_name = "N/A"
        if "lawyer_id" in h:
            try:
                lawyer = users.find_one({"_id": ObjectId(h["lawyer_id"])})
                if lawyer:
                    lawyer_name = lawyer.get("name", "N/A")
            except:
                pass

        h["case_title"] = case_title
        h["lawyer_name"] = lawyer_name

        # only upcoming logic
        h_date = datetime.strptime(h["hearing_date"], "%Y-%m-%d").date()
        h["is_upcoming"] = h_date >= today

        enriched_hearings.append(h)

    return render_template("admin_hearings.html", hearings=enriched_hearings)


# =======================search hearing=======================
@hearing_bp.route("/admin/search_hearing", methods=["GET"])
def search_hearing():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")

    query_input = request.args.get("query", "").strip()
    results = []

    if query_input:
        hearings_list = list(hearings.find())

        for h in hearings_list:
            h["_id"] = str(h["_id"])

            # Fetch case title
            case_title = "N/A"
            case_obj = None
            if "case_id" in h:
                try:
                    case_obj = cases.find_one({"_id": ObjectId(h["case_id"])})
                    if case_obj:
                        case_title = case_obj.get("title", "N/A")
                except:
                    pass

            # Fetch lawyer name
            lawyer_name_db = "N/A"
            if "lawyer_id" in h:
                try:
                    lawyer_obj = users.find_one({"_id": ObjectId(h["lawyer_id"])})
                    if lawyer_obj:
                        lawyer_name_db = lawyer_obj.get("name", "N/A")
                except:
                    pass

            # Detect if input is date (yyyy-mm-dd)
            is_date = False
            try:
                import datetime

                datetime.datetime.strptime(query_input, "%Y-%m-%d")
                is_date = True
            except:
                pass

            # Matching logic
            matched = False
            if is_date and h.get("hearing_date") == query_input:
                matched = True
            elif (
                query_input.lower() in case_title.lower()
                or query_input.lower() in lawyer_name_db.lower()
            ):
                matched = True

            if matched:
                h["case_title"] = case_title
                h["lawyer_name"] = lawyer_name_db
                results.append(h)

    error = None
    if not results and query_input:
        error = f"No hearings found for '{query_input}'"

    return render_template("search_hearing.html", hearings=results, error=error)
