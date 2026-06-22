from datetime import date, datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, session, g
from groq import Groq
from helpers import login_required
import markdown
import os
import psycopg2
from psycopg2 import pool
import psycopg2.extras
from werkzeug.security import check_password_hash, generate_password_hash

# Configure app
app = Flask(__name__)

# Default Flask Cookie sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
# Kick user out if inactive for more than 30 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Set up connection pool for speed
connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=os.environ.get("DATABASE_URL")
)

# Database connection
def get_db():
    global connection_pool
    # Check if connection is open in g
    if "db" not in g:
        # Test if the Neon database connection has not yet timed out, else replace connection
        try:
            conn = connection_pool.getconn()
            conn.cursor().execute("SELECT 1")
            g.db = conn
        # Create a new pool if the Neon DB connections have expired
        except Exception:
            connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=os.environ.get("DATABASE_URL")
            )
            # Borrow a new connection
            g.db = connection_pool.getconn()
        return g.db


# Close connection at end of every request
@app.teardown_appcontext
def close_db(error):
    # Remove connection from g else return None if there is no connection
    db = g.pop("db", None)
    # Close connection if active
    if db is not None:
        connection_pool.putconn(db)


@app.route("/")
def index():
    return redirect("/inventory")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Clear previous data for new user
        session.clear()
        session.permanent = True

        # Ensure the credentials are present and correct and log user in
        if not request.form.get("email") or not request.form.get("password"):
            flash("Please fill out all fields.", "warning")
            return redirect("/login")

        # Determine if account exists
        with get_db() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", [request.form.get('email')])
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
        with get_db() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", [request.form.get('email')])
                rows = cursor.fetchall()
        if len(rows) > 0:
            flash(
                f"Account with this email ({request.form.get('email')}) already exists.", "warning")
            return redirect("/register")

        # Add user to database
        with get_db() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("INSERT INTO users (email, hash) VALUES (%s, %s)",
                                [request.form.get("email"),
                                generate_password_hash(request.form.get("password"))
                                ])

        # Log user in
        with get_db() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", [request.form.get("email")])
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

    with get_db() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(f"SELECT * FROM ingredients WHERE user_id = %s ORDER BY {sort} NULLS LAST", [session["user_id"]])
            ingredients = cursor.fetchall()

    # Calculate days remaining
    for ingredient in ingredients:
        # Provided the ingredient has an expiry date
        if ingredient["expiry_date"]:
            expiry = ingredient["expiry_date"]
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
    name = request.form.get("name").title()
    amount = request.form.get("amount") or None
    metric = request.form.get("metric") or None
    expiry_date = request.form.get("expiry_date") or None
    with get_db() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("INSERT INTO ingredients (user_id, name, amount, metric, expiry_date) VALUES (%(user_id)s, %(name)s, %(amount)s, %(metric)s, %(expiry_date)s)", {
                    "user_id":session["user_id"],
                    "name":name,
                    "amount":amount,
                    "metric":metric,
                    "expiry_date":expiry_date
                    })

    return redirect("/inventory")

@app.route("/inventory/bulk-add", methods=["POST"])
@login_required
def inventory_bulk_add():
    # Get ingredient string
    ingredients = request.form.get("ingredients_input")
    if not ingredients:
        flash("Could not add Ingredient. Please include ingredient information.")
        return redirect("/inventory")
    
    # Format ingredients via Groq (handles variety in input better)

    system_prompt = f"""
                Today's date is {date.today().isoformat()}.
                You will be provided with a list of kitchen ingredients and will format it into a strict output as described below.
                The user has been instructed to place each ingredient and its details on a single line, creating a list of lines, each containing a unique ingredient's details.
                You have to format the ingredients given into a comma seperated output as per the format given below.
                If any ingredient details (such as the name, amount, metric, expiry_date) are missing you should enter "None" instead for that field.
                Your feedback/output may only consist of the comma seperated lines of ingredients. 
                You may never provide any comments or information other than the comma seperated lines of output.
                If a relative date is given for the expiry date, such as "7 days from now" or "2 weeks", calculate the date by adding the duration to today's date ({date.today().isoformat()}, and substitute that into the expiry date field. 
                If the date given excludes the year, assume that the current year is being referred to.
                Dates should be formatted to ISO format (yyyy-mm-dd).
                Spelling errors should be corrected in the output.
                Ingredient namees should be in title case.
                
                Output format to follow strictly:
                ingredient_name,amount,metric,expiry_date(ISO Format)
    """

    # Set up Groq exchange
    client = Groq(api_key=session.get("api_key"))

    # Send request
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
                "content": f"Here is the list of ingredients, each line describing a single ingredient: {ingredients}",
            }
        ],

        # The language model.
        model="llama-3.3-70b-versatile"
    )

    # Extract feedback
    csv_ingredients = chat_completion.choices[0].message.content

    # Loop through ingredients, validate and write to database
    with get_db() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            for ingredient_line in csv_ingredients.splitlines():
                name, amount, metric, expiry_date = ingredient_line.split(',')
                if name ==  "None":
                    flash("Could not add an ingredient. Ingredient Name was not found.")
                    continue
                
                if amount.strip() in ["None", "none"]:
                    amount = None
                if metric.strip() in ["None", "none"]:
                    metric = None
                if expiry_date.strip() in ["None", "none"]:
                    expiry_date = None
                else:
                    try:
                        expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d")
                    except (ValueError, TypeError):
                        expiry_date = None
                
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
    with get_db() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("DELETE FROM ingredients WHERE user_id = %s AND id = %s",
                    [session["user_id"],
                    request.form.get("ingredient_id")
                    ])
            
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
        with get_db() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", [session["user_id"]])
                rows = cursor.fetchall()
        if len(rows) > 0:
            # Update user account with api key
            with get_db() as connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("UPDATE users SET api_key = %s WHERE id = %s",
                            [request.form.get("api_key"),
                            session["user_id"]
                            ])
                    
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
    with get_db() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM ingredients WHERE user_id = %s ORDER BY expiry_date NULLS LAST", [session['user_id']])
            ingredients = cursor.fetchall()

    # Ensure there are enough ingredients for a recipe
    if len(ingredients) < 3:
        flash("Add at least 3 ingredients to generate a recipe.", "danger")
        return redirect("/inventory")

    ingredient_strings = []
    for ingredient in ingredients:
        if ingredient["amount"]:
            ingredient_strings.append(
                f"{ingredient['name']} ({ingredient['amount']}{ingredient['metric'] if ingredient['metric'] else ''})")
        else:
            ingredient_strings.append(f"{ingredient['name']}")

    ingredients_list = ", ".join(ingredient_strings)

    # System Prompt
    system_prompt = """
                    You are a helpful chef assistant.
                    Your primary goal is to generate a complete, and logical/culinary sound recipe.
                    When provided with a list of ingredients,
                    use them as the basisbut always prioritise generating a recipe that makes logical,
                    culinary sense over one that strictly matches what is listed.

                    Follow these principles:
                    - Always include standard kitchen ingredients as needed (such as salt, pepper, oil, common spices, water etc.) even if not listed.
                    - If the list of ingredients alone cannot produce a logical, complete and culinary sound dish, add the minimum
                        necessary ingredients to make it work. Mark any addeed ingredient not in the provided list with "(not in pantry)" next to it.
                    - Only mark an ingredient with "(not in pantry)" if it does not appear in the provided ingredients at all. 
                    - Do not annotate pantry ingredients with any reasoning or explanation.
                    - If you choose not to use a pantry ingredient, omit it from the recipe entirely. Do not list unused ingredients or explain the reason for skipping.
                    - Never attempt to make a dish if its key ingredients are missing (e.g. do not make donuts without flour, do not make pasta without pasta, flour & eggs or dough) 
                    - Use only the quantities that make culinary sense - do not use the full amount of an ingredient just because it is available or at the top of the expiry list.
                    - The list of ingredients is ordered by expiry date in ascending order.
                        Prioritize using ingredients at towards the start of the list.
                    - Be creative and avoid defaulting to the most obvious recipe.
                    - Explicitly state all ingredients used in the recipe as a whole under the ingredients heading.
                    - If a recipe involves pastry, dough or batter or any other ingredient in this category, include the preparation of it explicitly in the instructions. Do not assume it was pre-made.
                    - If one ingredient, like eggs, is used multiple times throughout a recipe, clearly state the amount to use for each usage of the ingredient.
            
                    Do not explain your analysis, comment on expiry dates or include any text outside of the recipe itself.

                    Format the recipe strictly as follows:
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