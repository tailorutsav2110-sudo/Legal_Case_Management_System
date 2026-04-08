from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
    current_app,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from bson.objectid import ObjectId
from db import documents, cases
from helpers.notify import notify_admin

document_bp = Blueprint("document", __name__)


# ================= ADMIN-LAWYER DOCUMENT REQUEST =================
@document_bp.route("/request/<case_id>", methods=["GET", "POST"])
def request_document(case_id):
    if session.get("role") not in ["admin", "lawyer"]:
        abort(403)

    if request.method == "POST":
        doc_name = request.form["doc_name"]

        documents.insert_one(
            {
                "case_id": ObjectId(case_id),
                "doc_name": doc_name,
                "status": "requested",
                "requested_by": session["user"],
                "uploaded_by": None,
                "file": None,
                "created_at": datetime.now(),
                "uploaded_at": None,
            }
        )

        return redirect(url_for("document.view_documents", case_id=case_id))

    return render_template("document_request.html", case_id=case_id)


# ================= CLIENT UPLOAD DOCUMENT =================
@document_bp.route("/upload/<doc_id>", methods=["GET", "POST"])
def upload_document(doc_id):
    if session.get("role") != "client":
        abort(403)

    doc = documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        abort(404)

    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)

        upload_path = os.path.join(current_app.root_path, "static/uploads", filename)
        file.save(upload_path)

        documents.update_one(
            {"_id": ObjectId(doc_id)},
            {
                "$set": {
                    "file": filename,
                    "status": "uploaded",
                    "uploaded_by": session["user"],
                    "uploaded_at": datetime.now(),
                }
            },
        )

        notify_admin(
            f"Client {session['user']} uploaded document '{doc.get('title', doc.get('doc_name'))}' for case"
        )  # notify_admin

        return redirect(url_for("document.view_documents", case_id=doc["case_id"]))

    return render_template("document_upload.html", doc=doc)


# ================= VIEW ALL DOCUMENTS OF CASE =================
@document_bp.route("/view/<case_id>")
def view_documents(case_id):
    if "user" not in session:
        return redirect("/login")

    docs = list(
        documents.find({"$or": [{"case_id": ObjectId(case_id)}, {"case_id": case_id}]})
    )
    for d in docs:
        d["_id"] = str(d["_id"])

    uploaded_files = []
    for d in docs:
        uploaded_files.append(
            {
                "_id": d["_id"],
                "file": d["file"],
                "doc_name": d["doc_name"],
                "status": d["status"],
            }
        )

    return render_template(
        "document_view.html", docs=uploaded_files, role=session["role"], case_id=case_id
    )


# ================= Delete document =================
@document_bp.route("/delete/<doc_id>")
def delete_document(doc_id):
    if "user" not in session:
        return redirect("/login")

    if session.get("role") not in ["admin", "lawyer"]:
        abort(403)

    doc = documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        abort(404)

    if doc.get("file"):
        try:
            file_path = os.path.join(
                current_app.root_path, "static/uploads", doc["file"]
            )
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print("Error deleting file:", e)

    documents.delete_one({"_id": ObjectId(doc_id)})

    return redirect(url_for("document.admin_document_requests", case_id=doc["case_id"]))


# ================= VIEW ALL DOCUMENTS OF ALL CASE =================
@document_bp.route("/admin/document_requests")
def admin_document_requests():
    if "user" not in session or session["role"] != "admin":
        return redirect("/login")

    all_docs = list(documents.find().sort("created_at", -1))

    enriched = []

    for d in all_docs:
        d_id = str(d["_id"])

        # ---- Get case details ----
        case_data = cases.find_one({"_id": ObjectId(d["case_id"])})
        case_title = case_data["title"] if case_data else "Unknown Case"

        enriched.append(
            {
                "_id": d_id,
                "case_title": case_title,
                "doc_name": d.get("doc_name"),
                "status": d.get("status"),
                "file": d.get("file"),
                "requested_at": d.get("created_at"),
                "requested_by": d.get("requested_by", "Unknown"),
                "uploaded_by": d.get("uploaded_by", "Unknown"),
                "case_id": str(d.get("case_id")),
            }
        )

    return render_template("admin_document_requests.html", requests=enriched)


# ================= Lawyer view all document of own cases =================
@document_bp.route("/documents")
def lawyer_documents():
    if "user" not in session or session["role"] != "lawyer":
        return redirect("/login")

    lawyer_id = session["user_id"]

    lawyer_cases = list(cases.find({"lawyer_id": lawyer_id}))

    lawyer_case_ids = [c["_id"] for c in lawyer_cases]

    if not lawyer_case_ids:
        return render_template("lawyer_document_requests.html", requests=[])

    docs = list(
        documents.find({"case_id": {"$in": lawyer_case_ids}}).sort("created_at", -1)
    )

    enriched = []

    for d in docs:
        case_id = d.get("case_id")

        case_data = cases.find_one({"_id": case_id, "lawyer_id": lawyer_id})

        if not case_data:
            continue

        enriched.append(
            {
                "_id": str(d["_id"]),
                "case_title": case_data.get("title", "Unknown Case"),
                "doc_name": d.get("doc_name"),
                "status": d.get("status"),
                "file": d.get("file"),
                "requested_at": d.get("created_at"),
                "requested_by": d.get("requested_by", "Unknown"),
                "uploaded_by": d.get("uploaded_by", "Unknown"),
                "case_id": str(case_id),
            }
        )

    return render_template("lawyer_document_requests.html", requests=enriched)


# ================= UPLOAD FILE =================
@document_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        os.path.join(current_app.root_path, "static/uploads"), filename
    )


# ======================= search document =======================
@document_bp.route("/search_document", methods=["GET"])
def search_document():
    if "user" not in session or session.get("role") not in ["admin", "lawyer"]:
        return redirect("/login")

    query_input = request.args.get("query", "").strip()
    results = []

    role = session.get("role")
    user_id = session.get("user_id")

    # get documents based on role
    if role == "admin":
        all_docs = list(documents.find())

    elif role == "lawyer":
        # Only cases of this lawyer
        lawyer_cases = list(cases.find({"lawyer_id": str(user_id)}))
        case_ids = [str(c["_id"]) for c in lawyer_cases]

        # Only documents of those cases
        all_docs = list(documents.find({"case_id": {"$in": case_ids}}))

    else:
        all_docs = []

    if query_input:
        for d in all_docs:
            d["_id"] = str(d["_id"])

            case_title = "Unknown Case"
            try:
                case_data = cases.find_one({"_id": ObjectId(d["case_id"])})
                if case_data:
                    case_title = case_data.get("title", "Unknown Case")
            except:
                pass

            uploaded_by = d.get("uploaded_by", "Unknown")

            if (
                query_input.lower() in case_title.lower()
                or query_input.lower() in str(uploaded_by).lower()
            ):
                results.append(
                    {
                        "_id": d["_id"],
                        "case_title": case_title,
                        "doc_name": d.get("doc_name"),
                        "status": d.get("status"),
                        "file": d.get("file"),
                        "requested_at": d.get("created_at"),
                        "requested_by": d.get("requested_by", "Unknown"),
                        "uploaded_by": uploaded_by,
                        "case_id": str(d.get("case_id")),
                    }
                )

    error = None
    if not results and query_input:
        error = f"No documents found for '{query_input}'"

    return render_template("search_document.html", documents=results, error=error)
