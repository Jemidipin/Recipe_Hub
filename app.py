from flask import Flask, render_template, request, redirect, flash, url_for, session
import mysql.connector
from mysql.connector import Error
import re
import time
import os
from werkzeug.utils import secure_filename
    
from datetime import datetime

UPLOAD_FOLDER = "static/upload"  # Define upload folder
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}  # Allowed file extensions

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    
    
app.secret_key = "your_secret_key"  # Needed for flash messages

# Database Connection
try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="123*root",
        database="recipehub",
        use_pure=True
    )
    mycursor = connection.cursor(buffered=True)
except Error as e:
    print("Error connecting to MySQL:", e)



@app.route("/")
def home():
    query = "SELECT * FROM RECIPES"
    mycursor.execute(query)
    recipes = mycursor.fetchall()  # Fetch all recipes from the database

    # Check if the user is logged in
    user_name = None
    if session.get("user_id"):  # If the user is logged in
        # Fetch the user's name from the database using the user_id in the session
        user_id = session.get("user_id")
        query_user = "SELECT username FROM users WHERE id = %s"  # Assuming the column is 'username'
        mycursor.execute(query_user, (user_id,))
        user_data = mycursor.fetchone()  # Fetch the user data

        if user_data:
            user_name = user_data[0]  # Access the username by index (0 for the first column)

    return render_template("home.html", recipes=recipes, user_name=user_name)




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        next_page = request.args.get("next")  # Get previous page URL

        # Fetch user from database
        query = "SELECT id, password FROM USERS WHERE EMAIL = %s"
        mycursor.execute(query, (email,))
        user = mycursor.fetchone()

        if user and password == user[1]:  # Plain-text password check
            session["user_id"] = user[0]  # Store user ID in session
            flash("Login successful!", "success")
            return redirect(next_page or url_for('home'))

            # Prevent open redirect attacks
            # if next_page and next_page.startswith("/"):
            #     return redirect(next_page)
            # return redirect(url_for("home", success="true"))  # Pass success flag

        else:
            flash("Invalid email or password. Please try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)  # Remove user from session
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        getusername = request.form.get("username")
        getemail = request.form.get("email")
        getpassword = request.form.get("password")
        confirm_password = request.form.get("confirm-password")

        # Validate passwords match
        if getpassword != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        # Validate email format
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, getemail):
            flash("Invalid email format!", "danger")
            return redirect(url_for("register"))

        # Insert user into database (PREVENT SQL INJECTION)
        try:
            query = "INSERT INTO USERS (USERNAME, EMAIL, PASSWORD) VALUES (%s, %s, %s)"
            data = (getusername, getemail, getpassword)
            mycursor.execute(query, data)
            connection.commit()
            
            # Send a success message to the frontend
            flash("Registration successful!", "success")
            return redirect(url_for("register", success="true"))  # Pass success flag to frontend
        except Error as e:
            flash("Error registering user: " + str(e), "danger")
            return redirect(url_for("register"))
    
    return render_template("register.html")

@app.route("/addrecipe", methods=["GET", "POST"])
def addrecipe():
    if "user_id" not in session:
        flash("Please log in to add a recipe.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        getname = request.form.get("name")
        getingredients = request.form.get("ingredients")
        getinstructions = request.form.get("instructions")
        getcooking_time = request.form.get("cooking_time")
        getserving_size = request.form.get("serving_size")
        getcategory = request.form.get("category")
        getuserid = session["user_id"]

        # Check if a file is uploaded
        if "photo" not in request.files:
            flash("No file uploaded!", "danger")
            return redirect(request.url)

        getimage = request.files["photo"]

        # Validate if a file is selected
        if getimage.filename == "":
            flash("No selected file!", "danger")
            return redirect(request.url)

        # Check file format and save
        if getimage and allowed_file(getimage.filename):
            filename = secure_filename(getimage.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            getimage.save(filepath)
        else:
            flash("Invalid file format. Please upload an image.", "danger")
            return redirect(request.url)

        # Save to database
        query = "INSERT INTO RECIPES (NAME, INGREDIENTS, INSTRUCTIONS, COOKING_TIME, SERVING_SIZE, CATEGORY, PHOTO, USER_ID) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        data = (getname, getingredients, getinstructions, getcooking_time, getserving_size, getcategory, filepath, getuserid)

        mycursor.execute(query, data)
        connection.commit()

        flash("Recipe added successfully!", "success")
        return redirect(url_for("home"))

    return render_template("addrecipe.html")

@app.route("/recipe", methods=["GET", "POST"])
def recipe():
        query = "SELECT * FROM RECIPES"
        mycursor.execute(query)
        recipes = mycursor.fetchall()  # Fetch all recipes from the database

        return render_template("recipe.html", recipes=recipes)
    
    

@app.route('/recipe/<int:recipe_id>', methods=['GET', 'POST'])
def recipe_detail(recipe_id):
    # Fetch recipe details
    query = "SELECT * FROM recipes WHERE id = %s"
    mycursor.execute(query, (recipe_id,))
    recipe = mycursor.fetchone()
    
    recipe_cat=recipe[6]
    
    allrec = "SELECT * FROM recipes where category = %s"
    mycursor.execute(allrec, (recipe_cat,))
    allrecipe = mycursor.fetchall()

    # Fetch comments for this recipe
    comments_query = "SELECT * FROM comments WHERE recipe_id = %s"
    mycursor.execute(comments_query, (recipe_id,))
    comments = mycursor.fetchall()

    # If the form is submitted (POST method), insert the comment
    
    if request.method == 'POST':
        user_id = session.get('user_id')  # assuming user is logged in and user_id is stored in session
        comment_text = request.form.get('comment')
        if comment_text:
            # Insert the comment into the database
            date_posted = datetime.now().date()  # current time
            insert_query = """
                INSERT INTO comments (user_id, recipe_id, comment, date_posted)
                VALUES (%s, %s, %s, %s)
            """
            mycursor.execute(insert_query, (user_id, recipe_id, comment_text, date_posted))
            connection.commit()  # Make sure to commit the transaction
            # Flash message for successful comment submission
            flash("Comment posted successfully!", "success")
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))  # Redirect to avoid form resubmission

    # If recipe exists, render the page
    if recipe:
        return render_template("recipe_detail.html", recipe=recipe, comments=comments, allrecipe=allrecipe)
    else:
        flash("Recipe not found.", "danger")
        return redirect(url_for("recipe"))



if __name__ == '__main__':
    app.run(debug=True)
