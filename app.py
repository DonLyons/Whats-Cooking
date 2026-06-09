from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash

# Configure app
app = Flask(__name__)

# Use local storage instead of browser cookies
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
db = SQL("sqlite:///whats_cooking.db")

@app.route("/")
def index():
    return redirect("/inventory")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Clear previous data for new user
    session.clear()

    if request.method == "POST":

        # DEV LOGIN REMOVE ======================================================
        if request.form.get("dev_sign_in") is not None:
            rows = db.execute("SELECT * FROM users WHERE email = ?", 'test@test.com')
            session["user_id"] = rows[0]["id"]
            return redirect("/inventory")
        # DEV LOGIN REMOVE ======================================================


        # Ensure the credentials are present and correct and log user in
        if not request.form.get("email") or not request.form.get("password"):
            flash("Please fill out all fields.", "warning")
            return redirect("/login")

        # Determine if account exists
        rows = db.execute("SELECT * FROM users WHERE email = ?", request.form.get('email'))
        if len(rows) > 0:
            if check_password_hash(rows[0]["hash"], request.form.get("password")):
                #log user in
                session["user_id"] = rows[0]["id"]
                return redirect("/inventory")
        flash("Invalid email or password.")
        return redirect("/login")
    else:
        # Display log in page
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Handle registration

        # Validation
        if not request.form.get("email") or not request.form.get("password") or not request.form.get("confirm"):
            flash("Please fill in all required fields to create an account.", "warning")
            return redirect("/register")
        elif request.form.get("password") != request.form.get("confirm"):
            flash("Passwords do not match.", "warning")
            return redirect("/register")

        # Basic Password and Email validation on html, TODO Live validation to be implemented

        # Ensure user is not already registered
        rows = db.execute("SELECT * FROM users WHERE email = ?", request.form.get("email"))
        if len(rows) > 0:
            flash(f"Account with this email ({request.form.get('email')}) already exists.", "warning")
            return redirect("/register")
            # TODO: Ask user if they want to proceed to login. Perhaps pop-up style

        # Add user to database
        db.execute("INSERT INTO users (email, hash) VALUES (?, ?)",
                   request.form.get("email"),
                   generate_password_hash(request.form.get("password"))
        )




        # Log user in
        rows = db.execute("SELECT * FROM users WHERE email = ?", request.form.get("email"))
        session["user_id"] = rows[0]["id"]
        # Inform user of success
        flash("Success! Welcome to What's Cooking?", "success")
        return redirect("/inventory")
    else:
        # Render page and allow for registration
        return render_template("register.html")

@app.route("/inventory")
@login_required
def inventory():
    # Show users ingredients/home page
    return render_template("inventory.html")


@app.route("/inventory/add")
@login_required
def inventory_add():
    # Add a new ingredient
    # Receive form data from inventory and add it to inventory
    return redirect("/inventory")


@app.route("/inventory/delete")
@login_required
def inventory_delete():
    # Remove ingredient
    # Receive ingredient id
    # Include user_id when deleting to ensure correct ingredient is removed
    # redirect back to inventory
    return redirect("/inventory")


@app.route("/settings")
@login_required
def settings():
    # Allow user to update or set their api key
    if request.method == "POST":
        # Handle api key addition
        if not request.form.get("api_key"):
            flash("Please provide an API Key.", "warning")
            return redirect("/settings")

        # Find user account
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        if len(rows) > 0:
            # Update user account with api key
            db.execute("UPDATE users SET api_key = ? WHERE id = ?", request.form.get("api_key"), session["user_id"])
            flash("Success! Your details have been updated", "success")
            return redirect("/settings")

        flash("Aw snap! Something went wrong. Please try logging in again.", "warning")
        return redirect("/settings")
    else:
        return render_template("settings.html")

@app.route("/recipe")
@login_required
def recipe():
    # Request recipe from API AI using most spoilt food in 'inventory'
    return

