#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Import pre-requisites.                                                     #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

import os
import io
import math
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from filestack import Client as FileStackClient, Security, Filelink
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

policy = {'expiry': 253381964415}
security = Security(policy, filestack_secret)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Testing connection                                                         #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/")
@app.route("/index", methods=["GET"])
def index():
    categories = mongo.db.categories.find().sort("category_name", 1)
    limit = 5
    uploads = mongo.db.uploads.find().sort("upload_time", -1).limit(limit)
    count_uploads = uploads.count()
    last_upload = int(math.ceil(count_uploads/limit))
    return render_template(
        "index.html", uploads=uploads,
        categories=categories, count_uploads=count_uploads,
        content=1, last_upload=last_upload)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Load more function                                                         #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/index/<content>", methods=["GET"])
def loadmore(content):
    categories = mongo.db.categories.find().sort("category_name", 1)
    all_uploads = mongo.db.uploads.find().sort("upload_time", -1)
    count_uploads = all_uploads.count()

    limit = 5
    offset = (int(content) - 1) * 5

    uploads = mongo.db.uploads.find().sort(
        "upload_time", -1).skip(offset).limit(limit)
    last_upload = int(math.ceil(count_uploads/limit))

    return render_template(
        "index.html", all_uploads=all_uploads,
        categories=categories, count_uploads=count_uploads,
        uploads=uploads, last_upload=last_upload, content=content)


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
        uploads = mongo.db.uploads.find().sort("upload_time", -1)
        comments = mongo.db.comments.find().sort("comment_time", -1)
        count_uploads = uploads.count()
        count_comments = comments.count()
        return render_template(
            "profile.html", username=username,
            uploads=uploads, count_uploads=count_uploads,
            comments=comments, count_comments=count_comments)

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
        # Checks if the title already exists
        existing_title = mongo.db.uploads.find_one({
            "upload_title": request.form.get("upload_title")})
        # if it exists it will let the user know
        if existing_title:
            flash("Title already exists")
            return redirect(request.referrer)

        file_object = request.files["file"].read()
        upload_image = file_object
        # when image is selected
        # then this function will be executed
        if upload_image:
            uploaded_file = filestack_client.upload(
                file_obj=io.BytesIO(file_object), security=security)
            upload = {
                "category_name": request.form.get("catergory_name"),
                "upload_title": request.form.get("upload_title"),
                "upload_description": request.form.get("upload_description"),
                "upload_image": uploaded_file.url,
                "upload_image_handle": uploaded_file.handle,
                "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
                "uploaded_by": session["user"]
                }
            mongo.db.uploads.insert_one(upload)
            flash("Congratulations {}, upload was succesfull!".format(
                    session["user"]))
            return redirect(url_for("index"))

        # if there is no image selected then this function will be executed
        else:
            upload = {
                "category_name": request.form.get("catergory_name"),
                "upload_title": request.form.get("upload_title"),
                "upload_description": request.form.get("upload_description"),
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
        existing_image = file_object
        # When there is already an uploaded image
        # and new image is selected
        # then this function will be executed
        if existing_image:
            overwrite_file = Filelink(upload["upload_image_handle"])
            file_object = request.files["file"].read()
            overwrite_file.overwrite(
                file_obj=io.BytesIO(file_object), security=security)
            mongo.db.uploads.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    "category_name": request.form.get("catergory_name"),
                    "upload_title": request.form.get("upload_title"),
                    "upload_description": request.form.get(
                        "upload_description"),
                    "upload_image": overwrite_file.url,
                    "upload_image_handle": overwrite_file.handle,
                    "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
                    "uploaded_by": session["user"]
                }}
            )
            flash(
                "Well done {},upload succesfully updated!".format(
                    session["user"]))
            return redirect(request.referrer)
        # When no image is selected
        # This function will be executed
        else:
            mongo.db.uploads.update_one(
                {"_id": ObjectId(id)},
                {"$set": {
                    "category_name": request.form.get("catergory_name"),
                    "upload_title": request.form.get("upload_title"),
                    "upload_description": request.form.get(
                        "upload_description"),
                    "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
                    "uploaded_by": session["user"]
                }}
            )
            flash(
                "Well done {},upload succesfully updated!".format(
                    session["user"]))
            return redirect(request.referrer)

        # when image is selected
        # then this function will update current values
        # elif new_image and not existing_image:
        #     uploaded_file = filestack_client.upload(
        #         file_obj=io.BytesIO(file_object), security=security)
        #     mongo.db.uploads.update_one(
        #         {"_id": ObjectId(id)},
        #         {"$set": {
        #             "category_name": request.form.get("catergory_name"),
        #             "upload_title": request.form.get("upload_title"),
        #             "upload_description": request.form.get(
        #                 "upload_description"),
        #             "upload_image": uploaded_file.url,
        #             "upload_image_handle": uploaded_file.handle,
        #             "upload_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
        #             "uploaded_by": session["user"]
        #         }}
        #     )
        #     flash(
        #         "Well done {},upload succesfully updated!".format(
        #             session["user"]))
        #     return redirect(request.referrer)
        # if there is no image selected
        # then this function will update current values

    return render_template(
        "edit_upload.html", upload=upload, categories=categories)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Delete Upload                                                              #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/delete_upload/<id>")
def delete_upload(id):
    mongo.db.uploads.remove({"_id": ObjectId(id)})
    flash("Upload succesfully deleted")
    return redirect(url_for("index"))


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Add a comment                                                              #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/add_comment/<id>", methods=["GET", "POST"])
def add_comment(id):
    upload = mongo.db.uploads.find_one({"_id": ObjectId(id)})
    new_comment = {
        "upload_title": request.form.get("upload_title"),
        "comment_by": session["user"],
        "comment_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
        "comment_description": request.form.get("comment_description")
    }

    if request.method == "POST":
        mongo.db.comments.insert_one(new_comment)
        flash(
            "Comment succesfully added, {}".format(session["user"]))
        return redirect(request.referrer)

    return render_template(request.referrer, upload=upload)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Edit Comment                                                               #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/edit_comment/<id>", methods=["GET", "POST"])
def edit_comment(id):
    comments = mongo.db.comments.find_one({"_id": ObjectId(id)})
    uploads = mongo.db.uploads.find()
    if request.method == "POST":
        mongo.db.comments.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "comment_time": datetime.now().strftime("%Y-%m-%d, %H:%M"),
                "comment_description": request.form.get("comment_description")
            }})
        flash("Comment succesfully changed")
        return redirect(request.referrer)
    return render_template(
        "edit_comment.html", comments=comments, uploads=uploads)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Categories                                                                 #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/all_categories")
def all_categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("all_categories.html", categories=categories)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Browse categories                                                          #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/category_page/<category_name>", methods=["GET"])
def category_page(category_name):
    uploads = mongo.db.uploads.find({
        "category_name": category_name}).sort("upload_time", -1)
    return render_template("category.html", uploads=uploads)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Upload on a single page                                                    #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

@app.route("/upload_page/<id>", methods=["GET", "POST"])
def upload_page(id):
    comments = list(
        mongo.db.comments.find().sort("comment_time", -1))
    upload = mongo.db.uploads.find_one({"_id": ObjectId(id)})
    return render_template("upload.html", upload=upload, comments=comments)


#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #
#  Development/Production environment test for debug                          #
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  #

if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
# return to debug=false when actual deployment / project submit.
