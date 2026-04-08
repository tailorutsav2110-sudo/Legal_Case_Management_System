from flask import Blueprint,render_template,request,redirect,session
from db import users
from extensions import bcrypt


auth_bp = Blueprint("auth",__name__)

@auth_bp.route("/")
def home():
    return render_template("home.html")

# =======================login detalis=======================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        # Basic validations 
        if not email or not password or not role:
            error = "All fields are required"
            return render_template("login.html", error=error)

        # User validation 
        user = users.find_one({"email": email, "role": role})

        if not user:
            error = "Invalid email or role"
            return render_template("login.html", error=error)

        if not bcrypt.check_password_hash(user["password"], password):
            error = "Incorrect password"
            return render_template("login.html", error=error)

        # Session set
        session["user_id"] = str(user["_id"])
        session["user"] = user["name"]
        session["role"] = user["role"]

        # Role based redirect
        if role == "admin":
            return redirect("/admin_dashboard")
        elif role == "lawyer":
            return redirect("/dashboard")
        elif role == "staff":
            return redirect("/staff/dashboard")
        else:
            return redirect("/client_dashboard")

    return render_template("login.html")

# =======================register details=======================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "").strip().lower()
        password = request.form.get("password", "").strip()

        # Basic validations
        # if not name or not email or not role or not password:
        #     error = "All fields are required"
        #     return render_template("register.html", error=error)

        # if len(password) < 6:
        #     error = "Password must be at least 6 characters"
        #     return render_template("register.html", error=error)

        # # Duplicate email check 
        # if users.find_one({"email": email}):
        #     error = "Email already registered"
        #     return render_template("register.html", error=error)

        # Insert user
        users.insert_one({
            "name": name,
            "email": email,
            "role": role,
            "password": bcrypt.generate_password_hash(password)
        })

        return redirect("/login")

    return render_template("register.html")

@auth_bp.route("/about")
def about():
    return render_template("about.html")

@auth_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # For now just print (test)
        print(name, email, message)

        return render_template("contact.html", success=True)

    return render_template("contact.html")
# =======================logout details=======================
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")

