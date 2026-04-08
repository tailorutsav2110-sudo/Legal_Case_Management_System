# download [python -m pip install xhtml2pdf]

from flask import Blueprint, render_template, session, make_response
from bson import ObjectId
from datetime import date, datetime
from db import cases, hearings, documents
from xhtml2pdf import pisa
from io import BytesIO

report_bp = Blueprint("report", __name__)


# ====================== Case Summary Report ======================
@report_bp.route("/reports/cases")
def case_report():
    if "user" not in session:
        return "Unauthorized", 401

    # Fetch all cases (only once)
    all_cases = list(cases.find())

    for case in all_cases:
        case["_id"] = str(case["_id"])

    total_cases = len(all_cases)
    open_cases = len([c for c in all_cases if c.get("status") == "Open"])
    pending_cases = len([c for c in all_cases if c.get("status") == "Pending"])
    closed_cases = len([c for c in all_cases if c.get("status") == "Closed"])

    return render_template(
        "reports/case_report.html",
        cases=all_cases,
        total_cases=total_cases,
        open_cases=open_cases,
        pending_cases=pending_cases,
        closed_cases=closed_cases,
    )


# ====================== Case Summary Report Export to Pdf ======================
@report_bp.route("/reports/cases/pdf")
def case_report_pdf():
    if "user" not in session:
        return "Unauthorized", 401

    all_cases = list(cases.find())

    for case in all_cases:
        case["_id"] = str(case["_id"])

    total_cases = len(all_cases)
    open_cases = len([c for c in all_cases if c.get("status") == "Open"])
    pending_cases = len([c for c in all_cases if c.get("status") == "Pending"])
    closed_cases = len([c for c in all_cases if c.get("status") == "Closed"])

    html = render_template(
        "reports/case_report_pdf.html",
        cases=all_cases,
        total_cases=total_cases,
        open_cases=open_cases,
        pending_cases=pending_cases,
        closed_cases=closed_cases,
    )

    result = BytesIO()
    pisa.CreatePDF(html, dest=result)

    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=case_report.pdf"
    return response


# ====================== Hearing Summary Report ======================
@report_bp.route("/reports/hearings")
def hearing_report():
    if "user" not in session:
        return "Unauthorized", 401

    all_hearings = list(hearings.find())
    today = date.today()

    for h in all_hearings:
        h["_id"] = str(h["_id"])

        hearing_date = h.get("hearing_date")

        if hearing_date:
            h["date_str"] = hearing_date

            # upcoming logic
            h_date = datetime.strptime(hearing_date, "%Y-%m-%d").date()
            h["is_upcoming"] = h_date >= today
        else:
            h["date_str"] = "N/A"
            h["is_upcoming"] = False

    upcoming = [h for h in all_hearings if h["is_upcoming"]]

    return render_template(
        "reports/hearing_report.html",
        hearings=all_hearings,
        upcoming_count=len(upcoming),
    )


# ====================== Hearing Summary Report Export to Pdf ======================
@report_bp.route("/reports/hearings/pdf")
def hearing_report_pdf():
    if "user" not in session:
        return "Unauthorized", 401

    all_hearings = list(hearings.find())
    today = date.today()

    for h in all_hearings:
        h["_id"] = str(h["_id"])

        if h.get("hearing_date"):
            try:
                h_date = datetime.strptime(h["hearing_date"], "%Y-%m-%d")
                h["date_obj"] = h_date
                h["date_str"] = h["hearing_date"]

                # upcoming flag
                h["is_upcoming"] = h_date.date() >= today

            except:
                h["date_obj"] = None
                h["date_str"] = "N/A"
                h["is_upcoming"] = False
        else:
            h["date_obj"] = None
            h["date_str"] = "N/A"
            h["is_upcoming"] = False

    upcoming = [h for h in all_hearings if h["is_upcoming"]]

    html = render_template(
        "reports/hearing_report_pdf.html",
        hearings=all_hearings,
        upcoming_count=len(upcoming),
    )

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        return "Error generating PDF", 500

    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=hearing_report.pdf"
    return response


# ====================== Document Summary Report ======================
@report_bp.route("/reports/documents")
def document_report():
    if "user" not in session:
        return "Unauthorized", 401

    all_docs = list(documents.find())

    uploaded_count = 0
    not_uploaded_count = 0
    for d in all_docs:
        # Convert ObjectIds to strings
        d["_id"] = str(d["_id"])
        d["case_id"] = str(d.get("case_id", "N/A"))

        d["_id_short"] = d["_id"][:5]
        d["case_id_short"] = d["case_id"][:5]

        # Ensure status is a string and compare safely
        status = str(d.get("status") or "").strip().lower()
        if status == "uploaded":
            uploaded_count += 1
        else:
            not_uploaded_count += 1

    # Count document types
    doc_types = {}
    for doc in all_docs:
        t = doc.get("type", "Unknown")
        doc_types[t] = doc_types.get(t, 0) + 1

    return render_template(
        "reports/document_report.html",
        documents=all_docs,
        doc_types=doc_types,
        uploaded_count=uploaded_count,
        not_uploaded_count=not_uploaded_count,
    )


# ====================== Document Summary Report Export to PDF ======================
@report_bp.route("/reports/documents/pdf")
def document_report_pdf():
    if "user" not in session:
        return "Unauthorized", 401

    all_docs = list(documents.find())

    uploaded_count = 0
    not_uploaded_count = 0
    for doc in all_docs:
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        doc["case_id"] = str(doc.get("case_id", "N/A"))

        doc["_id_short"] = doc["_id"][:5]
        doc["case_id_short"] = doc["case_id"][:5]

        status = str(doc.get("status") or "").strip().lower()
        if status == "uploaded":
            uploaded_count += 1
        else:
            not_uploaded_count += 1

        if doc.get("uploaded_at"):
            doc["uploaded_at"] = doc["uploaded_at"].strftime("%Y-%m-%d %H:%M")
        else:
            doc["uploaded_at"] = "N/A"

    html = render_template(
        "reports/document_report_pdf.html",
        documents=all_docs,
        uploaded_count=uploaded_count,
        not_uploaded_count=not_uploaded_count,
    )

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return "Error generating PDF", 500

    response = make_response(result.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=document_report.pdf"
    return response
