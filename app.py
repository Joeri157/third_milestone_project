#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Import pre-requisites.                                                     #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

import os
import io
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from filestack import Client as FileStackClient, Security
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Connect to external MongoDB database                                       #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

app = Flask(__name__)
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
filestack_client = FileStackClient(os.environ.get("FILE_STACK_PUBLIC_API_KEY"))
filestack_secret = os.environ.get("FILE_STACK_SECRET_API_KEY")

mongo = PyMongo(app)

policy = {"expiry": 253381964415}


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Testing connection                                                         #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/")
@app.route("/index")
def index():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    uploads = list(
        mongo.db.uploads.find().sort("upload_time", -1))
    return render_template(
        "index.html", uploads=uploads, categories=categories)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Registration                                                               #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))
        #  Registers new users to the db
        register = {
            "first_name": request.form.get("first_name").lower(),
            "last_name": request.form.get("last_name").lower(),
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        #  put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Sing Up Succesfull, {}".format(request.form.get("username")))
        return redirect(url_for("profile", username=["user"]))

    return render_template("register.html")


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Log In                                                                     #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/login", methods=["GET", "POST"])
def login():
    # check if username exists in db
    if request.method == "POST":
        existing_user = mongo.db.users.find_one({
            "username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    session["user"] = request.form.get("username").lower()
                    flash("Welcome, {}".format(
                        request.form.get("username")))
                    return redirect(url_for(
                        "profile", username=["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))
    return render_template("login.html")


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Profile                                                                    #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab's the session username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    if session["user"]:
        uploads = list(
            mongo.db.uploads.find().sort("upload_time", -1))
        return render_template(
            "profile.html", username=username, uploads=uploads)

    return redirect(url_for("login"))


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Log out                                                                    #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/logout")
def logout():
    # remove user from session cookies
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Add Upload                                                                 #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/add_upload", methods=["GET", "POST"])
def add_upload():
    categories = mongo.db.categories.find().sort("category_name", 1)
    if request.method == "POST":
        file_object = request.files["upload_image"].read()
        security = Security(policy, filestack_secret)
        uploaded_file = filestack_client.upload(
            file_obj=io.BytesIO(file_object), security=security)
        upload = {
            "category_name": request.form.get("catergory_name"),
            "upload_title": request.form.get("upload_title"),
            "upload_description": request.form.get("upload_description"),
            "upload_image": uploaded_file.url,
            "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
            "uploaded_by": session["user"]
            }
        mongo.db.uploads.insert_one(upload)
        flash("Congratulations {}, upload was succesfull!".format(
                session["user"]))
        return redirect(url_for("index"))

    return render_template("add_upload.html", categories=categories)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Edit Upload                                                                #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/edit_upload/<id>", methods=["GET", "POST"])
def edit_upload(id):
    upload = mongo.db.uploads.find_one({"_id": ObjectId(id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    if request.method == "POST":
        file_object = request.files["file"].read()
        security = Security(upload_only_policy, filestack_secret)
        overwrite_file = filestack_client.upload(
            file_obj=io.BytesIO(file_object), security=security)
        mongo.db.uploads.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "category_name": request.form.get("catergory_name"),
                "upload_title": request.form.get("upload_title"),
                "upload_description": request.form.get("upload_description"),
                "upload_image": overwrite_file.url,
                "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
                "uploaded_by": session["user"]
            }}
        )
        flash(
            "Well done {},upload succesfully updated!".format(session["user"]))
        return redirect(url_for("index"))

    return render_template(
        "edit_upload.html", upload=upload, categories=categories)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Upload on a single page                                                    #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/upload_page/<id>", methods=["GET", "POST"])
def upload_page(id):
    upload = mongo.db.uploads.find_one({"_id": ObjectId(id)})
    return render_template("upload.html", upload=upload)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Development/Production environment test for debug                          #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
# return to debug=false when actual deployment / project submit.
