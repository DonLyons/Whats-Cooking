from datetime import date
from flask import Flask, flash, redirect, render_template, request, session
from groq import Groq
from helpers import login_required
import markdown
import os
import psycopg2
import psycopg2.extras
from werkzeug.security import check_password_hash, generate_password_hash

# Configure app
app = Flask(__name__)

# Default Flask Cookie sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

# Set up database
connection = psycopg2.connect(os.environ.get("DATABASE_URL"))


@app.route("/")
def index():
    return redirect("/inventory")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Clear previous data for new user
        session.clear()

        # Ensure the credentials are present and correct and log user in
        if not request.form.get("email") or not request.form.get("password"):
            flash("Please fill out all fields.", "warning")
            return redirect("/login")

        # Determine if account exists
        with connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", request.form.get('email'))
                rows = cursor.fetchall()

        if len(rows) > 0:
            if check_password_hash(rows[0]["hash"], request.form.get("password")):
                # Log user in
                session["user_id"] = rows[0]["id"]
                if rows[0]["api_key"] is not None:
                    session["api_key"] = rows[0]["api_key"]
                return redirect("/inventory")
        flash("Invalid email or password.", "danger")
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
        with connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", request.form.get("email"))
                rows = cursor.fetchall()
        if len(rows) > 0:
            flash(
                f"Account with this email ({request.form.get('email')}) already exists.", "warning")
            return redirect("/register")
            # TODO: Ask user if they want to proceed to login. Perhaps pop-up style

        # Add user to database
        with connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("INSERT INTO users (email, hash) VALUES (%s, %s)",
                                request.form.get("email"),
                                generate_password_hash(request.form.get("password"))
                                )

        # Log user in
        with connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", request.form.get("email"))
                rows = cursor.fetchall()
        session["user_id"] = rows[0]["id"]
        # Inform user of success
        flash("Success! Welcome to What's Cooking?", "success")
        return redirect("/inventory")
    else:
        # Render page and allow for registration
        return render_template("register.html")


@app.route("/inventory", methods=["GET"])
@login_required
def inventory():
    # Show users ingredients/home page

    # Sorting:
    sorts = ["name", "expiry_date", "amount"]

    #   Get sort method from sort var, else use sort by name
    sort = request.args.get("sort", "expiry_date")

    # Validate sorting method to avoid SQL injection
    if sort not in sorts:
        sort = "expiry_date"

    with connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(f"SELECT * FROM ingredients WHERE user_id = %s ORDER BY {sort} NULLS LAST", session["user_id"])
            ingredients = cursor.fetchall()

    # Calculate days remaining
    for ingredient in ingredients:
        # Provided the ingredient has an expiry date
        if ingredient["expiry_date"]:
            expiry = date.fromisoformat(ingredient["expiry_date"])
            days_remaining = (expiry - date.today()).days
            ingredient["days_remaining"] = days_remaining
        else:
            ingredient["days_remaining"] = None

    return render_template("inventory.html", ingredients=ingredients, sort=sort)


@app.route("/inventory/add", methods=["POST"])
@login_required
def inventory_add():
    # Add a new ingredient
    if not request.form.get("name"):
        flash("Could not add Ingredient. Please include an Ingredient Name")
        return redirect("/inventory")
    name = request.form.get("name")
    amount = request.form.get("amount") or None
    metric = request.form.get("metric") or None
    expiry_date = request.form.get("expiry_date") or None
    with connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("INSERT INTO ingredients (user_id, name, amount, metric, expiry_date) VALUES (%(user_id)s, %(name)s, %(amount)s, %(metric)s, %(expiry_date)s)", {
                    "user_id":session["user_id"],
                    "name":name,
                    "amount":amount,
                    "metric":metric,
                    "expiry_date":expiry_date
                    })

    return redirect("/inventory")


@app.route("/inventory/delete", methods=["POST"])
@login_required
def inventory_delete():
    # Remove ingredient
    # Include user_id when deleting to ensure correct ingredient is removed
    with connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("DELETE FROM ingredients WHERE user_id = %s AND id = %s",
                    session["user_id"],
                    request.form.get("ingredient_id")
                    )
            
    flash("Item removed.", "success")
    # redirect back to inventory
    return redirect("/inventory")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    # Allow user to update or set their api key
    if request.method == "POST":
        # Handle api key addition
        if not request.form.get("api_key"):
            flash("Please provide an API Key.", "warning")
            return redirect("/settings")

        # Find user account
        with connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", session["user_id"])
                rows = cursor.fetchall()
        if len(rows) > 0:
            # Update user account with api key
            with connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("UPDATE users SET api_key = %s WHERE id = %s",
                            request.form.get("api_key"),
                            session["user_id"]
                            )
            session["api_key"] = request.form.get("api_key")
            flash("Success! Your details have been updated", "success")
            return redirect("/settings")

        flash("Aw snap! Something went wrong. Please try logging in again.", "warning")
        return render_template("settings.html", api_key=session["api_key"])
    else:
        return render_template("settings.html", api_key=session.get("api_key"))


@app.route("/recipe", methods=["GET"])
@login_required
def recipe():
    # Ensure user has an API key
    if session.get("api_key") is None:
        flash("Please provide an API Key below to enable recipe generation.", "warning")
        return redirect("/settings")

    # Determine ingredients list
    with connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM ingredients WHERE user_id = %s ORDER BY expiry_date NULLS LAST", session["user_id"])
            ingredients = cursor.fetchall()

    # Ensure there are enough ingredients for a recipe
    if len(ingredients) < 3:
        flash("Add at least 3 ingredients to generate a recipe.", "danger")
        return redirect("/inventory")

    ingredient_strings = []
    for ingredient in ingredients:
        if ingredient["amount"]:
            ingredient_strings.append(
                f"{ingredient['name']} ({ingredient['amount']}{ingredient['metric']})")
        else:
            ingredient_strings.append(f"{ingredient["name"]}")

    ingredients_list = ", ".join(ingredient_strings)

    # System Prompt
    system_prompt = """
                    You are a helpful chef assistant.
                    When provided with a list of ingredients, generate a detailed and clear recipe.
                    The list of ingredients is ordered by expiry date in ascending order.
                    Prioritize using ingredients at the beginning of the list.
                    Do not mention your analysis of the ingredients or which is closest to expiring.
                    Feedback should only be the recipe itself.
                    Be creative and avoid defaulting to obvious recipes.

                    Format the recipe as follows:
                    # [Recipe Title]

                    Servings: [number] | Calories per serving: [number] | Total time: [duration]

                    ### Ingredients
                    - [ingredient and quantity]

                    ### Instructions
                    1. [step]
                    2. [step]

                    Use only the headings shown above. Do not use headings for servings, calories or time. Those are for the summary line.
                    The recipe should be neatly formatted with:
                    - A creative title
                    - Total number of servings yielded
                    - Calories per serving
                    - Total time to make
                    - Ingredients
                    - Numbered list of Step-by-Step instructions
                    The recipe should be well formatted with the Recipe Name, an Ingredients and an Instructions heading.
                    """

    # Fetch recipe through Groq API
    client = Groq(api_key=session.get("api_key"))

    chat_completion = client.chat.completions.create(
        messages=[
            # System Message
            {
                "role": "system",
                "content": system_prompt,
            },
            # Set a user message for the assistant to respond to.
            {
                "role": "user",
                "content": f"I have these ingredients: {ingredients_list}. What can I make?",
            }
        ],

        # The language model.
        model="llama-3.3-70b-versatile"
    )

    recipe_text = chat_completion.choices[0].message.content
    recipe_html = markdown.markdown(recipe_text)
    # Render recipe
    return render_template("recipe.html", recipe=recipe_html)

if __name__ == "__main__":
    app.run()