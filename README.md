<h1>
    &nbsp;
    <img src="static/cooking_grey.svg" width="50" valign="middle"/>
    &nbsp;
    What's Cooking?
</h1>

> **An AI-powered pantry manager that generates creative recipes from ingredients you have and prioritizing what's closest to expiry so nothing goes to waste.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-00000?style=flat&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=flat&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat&logo=bootstrap&logoColor=white)
![Groq](https://img.shields.io/badge/Groq%20API-LLaMA--3.3--70B-F55036?style=flat)
![Render](https://img.shields.io/badge/Hosted_on-Render-46E3B7?style=flat&logo=render&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

**[Live Hosted Demo](https://whats-cooking-zvk1.onrender.com/)** - Try it! &nbsp; **|** &nbsp; **[Video Demo](https://youtu.be/76ibmWeKFpk)** - Watch it!

> Note: Render's free tier spins down after inactivity. The first load may take 30-60 seconds to wake up.


## The Problem It Solves
How often have you thrown out food because you forgot it was in the furthest corner of the fridge? ***What's Cooking?*** keeps track of your pantry, warns you when items are expiring soon, and uses AI to generate a recipe that makes use of them before they become waste.

## Features

- **User authentication**
    - Secure registration and login with Werkzeug password hashing
- **Persistent pantry management**
    - Add ingredients with optional inputs (amount, unit & expiry), delete with one click
- **Expiry tracking**
    - Colour-coded countdown badges show what's expiring soon (red <= 2 days, amber <= 7 days & green for expiry dates further away)
- **Smart sorting** 
    - Sort the pantry by expiry date, name, or amount. NULL expiry dates always sort last
- **AI recipe generation**
    - Single click recipe generation via Groq's LLaMA 3.3 70B, which has been prompted to prioritise soon-to-expire elements
- **User Unique API Key storage**
    - Users supply their own Groq API key, stored securely in the database
- **Responsive Design**
    - Bootstrap 5.3 Styling with a custom street-food colour palette. Mobile friendly design

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Database | PostgreSQL via [Neon](https://neon.tech) (`psycopg2`) |
| AI | Groq API: LLaMA 3.3 70B Versatile |
| Frontend | Bootstrap 5.3, Jinja, JS |
| Auth | Werkzeug (`generate_password_hash` / `check_password_hash`) |
| Markdown | `markdown` library (used to render AI recipe output) |
| Sessions | Flask cookie-based sessions |
| Hosting | [Render](https://render.com) (web service) |

## Project Structure

Whats-Cooking/
├── app.py                  # Flask routes and logic
├── helpers.py              # login_required decorator
├── requirements.txt
├── static/
│   ├── styles.css          # Custom CSS with CSS variable theming
│   └── cooking.svg         # App logo 
└── templates/
    ├── layout.html         # Base Jinja template (navbar, flash messages)
    ├── login.html
    ├── register.html
    ├── inventory.html      # Pantry Management
    ├── recipe.html         # AI-generated recipe display
    └── settings.html       # Groq API key management

## How It Works

### Expiry First Recipe Generation

When the user hits *Generate Smart Recipe*, the app:
1. Fetches all the users ingredients from PostgreSQL, ordered by `expiry_date NULLS LAST`
2. Builds a comma-separated ingredients string (including amounts where present)
3. Sends a structured prompt, including the ingredients string to Groq API, instructing the model to prioritise ingredients at the beginning of the list.
4. Extracts the models output and converts it from markdown to HTML to render it in the browser.

```python
cursor.execute(
    "SELECT * FROM ingredients WHERE user_id = %s ORDER BY expiry_date NULLS LAST", [session["user_id"]]
)
```

### SQL Injection Protection

The pantry sort parameters, passed via URL args, are first validated against a set list of valid sorts before being used in the query, preventing malicious injections.

```python
sorts = ["name", "expiry_date", "amount"]
sort = request.args.get("sort", "expiry_date")
if sort not in sorts:
    sort = "expiry_date"
```

### NULL Storage and Sorting Bugs Prevention

Optional input fields in ingredients are converted to None when empty rather than storing empty strings. This ensures `ORDER BY ... NULLS LAST` sorts correctly and predictably for various inputs.

```python
amount = request.form.get("amount") or None
expiry_date = request.form.get("expiry_date") or None
```

## Design Choices

***Persistent ingredient storage over session-based storage?*** Having to re-enter your entire pantry on every visit would be time-consuming. Persistent storage linked to your account creates a time-friendly flow: log-In, add new ingredients as you get them and generate recipes whenever you need them. No need to setup each time.

***Why Groq?*** Groq has a reputation for significantly faster responses than it's competitors and has a generous free tier based on my research. This speed and availability to all types of users matters most, iially when delays can heavily affect the user's experience.

***Why user-supplied API Keys?*** Rather than embedding a single API key, which would exhaust usage limits quickly, each user uses their own key. This makes the app more secure and scalable with each user handling the security of their own key.

***Why prioritize expiring ingredients*** The main focus of the app is reducing food waste. Sorting ingredients by expiry date and prompting the model to use foods towards the top of the list (closest to expiry) ensures recipes are useful and appealling. It's not just a random recipe but one tailored to your pantry right now.

***Why PostgreSQL over SQLite?*** SQLite was great for development but not applicable for deployment. Migrating to PostgreSQL hosted on Neon made deploying on Render easy and database interactions smooth while giving the app a real production-grade database.

## Getting Started!

### Try the Live App
The easiest way is the [hosted version on Render](https://whats-cooking-zvk1.onrender.com/). Register, grab an API key from [Groq]() and you are all set! Lettuce celebrate! (Get it? 🥬)

## Future Improvements

- [ ] Live JS client-side password validation on registration
- [ ] Photo upload - scan packaging with AI to auto-fill ingredient details
- [ ] Edit ingredient quantities/details in-place (currently requires delete & re-add)
- [ ] Save and browse previously generated recipes
- [ ] Export recipes
- [ ] Add dietary preference before generation

## Acknowledgements

- [CS50x](https://cs50.harvard.edu/x/) - Harvard's Introduction to Computer Science
- [Groq](https://groq.com) - Fast, free LLM API
- [Bootstrap](https://getbootstrap.com) - UI framework
- [Flaticon](https://www.flaticon.com/) - Website logo
- [favicon.io](https://favicon.io) - Browser tab icon

---

*Initially built from scratch as a CS50 final project, refined for portfolio piece demonstrating full-stack Python web development.*
