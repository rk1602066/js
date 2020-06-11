ECHO is on.
import os
import requests
from flask import Flask, session,render_template,request,url_for,redirect,flash,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
from datetime import datetime

app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['JSON_SORT_KEYS'] = False
app.config['SECRET_KEY'] = "SECRET_KEY"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        hashed_password = sha256_crypt.encrypt(str(password))

        if password==confirm_password:
            users = db.execute("select username from users where username = :username",{"username":username}).fetchone()

            emails = db.execute("select email from users where email = :email",
                               {"email": email}).fetchone()

            is_no_user = users is None ;is_no_email = emails is None

            if users is None and emails is None:
                db.execute("insert into users (email,username,password) values (:email,:username,:password)",
                           {"email": email, "username": username, "password": hashed_password})
                db.commit()
                flash("You are Successfully registered, Can login now", "success")
                return redirect(url_for("login"))

            else:

                if is_no_user:
                    flash("email is not available","danger")

                elif is_no_email:
                    flash("username is not available","danger")

                else:
                    flash("username and email is not available","danger")

                render_template("register.html")
        else:
            flash("Password doesn't match","danger")

    return render_template("register.html")


@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        username_data = db.execute("select username from users where username = :username",{"username":username}).fetchone()
        password_data = db.execute("select password from users where username = :username",{"username":username}).fetchone()
        if username_data is None:
            flash("No such user found","danger")
            return render_template("login.html")
        else:
            for passw in password_data:
                if sha256_crypt.verify(password,passw):
                    session["log"]=True
                    session["username"] = username
                    flash("You are logged in","success")
                    return redirect(url_for("search"))
                else:
                    flash("Incorrect username or password ","danger")
    return render_template("login.html")


@app.route("/search")
def search():
    return render_template("search.html")


@app.route("/books",methods=["GET","POST"])
def books():
    if request.method == "POST":
        search_input = request.form.get("search_input")
        query = "%" + search_input+ "%"
        query = query.title()

        rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                                isbn LIKE :query OR \
                                title LIKE :query OR \
                                author LIKE :query LIMIT 15",
                          {"query": query})
        if rows.rowcount == 0:
            return render_template("404.html", message="we can't find books with that description.")


        flash("your search results are ready","success")

        books = rows.fetchall()

        return render_template( "books.html",books=books)

    else:
        flash("something went wrong. please try again","danger")

    return render_template("search.html")


@app.route("/error")
# inbuilt function which takes error as parameter
def error():
    # defining function
    return render_template("404.html")


@app.route("/books/<string:book_isbn>",methods=["GET","POST"])
def book(book_isbn):

        reviews = db.execute("select * from reviews where book_isbn = :book_isbn",{"book_isbn":book_isbn}).fetchall()

        book = db.execute("select * from books where isbn = :book_isbn",
                            {"book_isbn": book_isbn}).fetchone()

        try:
            res = requests.get("https://www.goodreads.com/book/review_counts.json",
                               params={"key": "HsHeS0VC5TPgUSHFlFbE3Q", "isbns": book_isbn})
            goodreads = res.json()
            data = goodreads['books'][0]
        except:
            return render_template("404.html",message = "goodreads taking too much time for response")

        if not len(reviews):
            message = "No reviews yet !!!"
        else:
            message = "All reviews are : "
        return render_template("book.html",book=book,data=data,reviews=reviews,message=message)


@app.route("/books/<string:book_isbn>/success",methods=["GET","POST"])
def success(book_isbn):
    if request.method == "POST":
        rating = request.form.get("rating")
        review = request.form.get("review")

        username =session["username"]

        reviewers = db.execute("SELECT reviewers_name FROM reviews WHERE reviewers_name=:reviewers_name AND book_isbn=:book_isbn",
                               {"reviewers_name":username,"book_isbn":book_isbn}).fetchall()
        datetimes = datetime.now()
        dates = str(datetimes.date())+" "+str(datetimes.hour)+":"+str(datetimes.minute)
        if not len(reviewers):
            db.execute("insert into reviews (rating,review,book_isbn,reviewers_name,datetime) values (:rating,:review,:book_isbn,:reviewers_name,:datetime)",
                       {"rating": rating, "review": review, "book_isbn": book_isbn, "reviewers_name": username,"datetime":dates})
            db.commit()

            flash("Successfully saves your review", "success")
        else:
            flash("You have already rate this book. So you cant review again", "danger")
        return redirect(url_for("book", book_isbn=book_isbn))

    else:
        flash("Something went wrong!! please try again","danger")
    return redirect(url_for("error",message = "Something went wrong!! please try again"))



@app.route("/logout",)
def logout():
    session["log"]=False
    session.pop('username', None)
    flash("You are logged out","success")
    return redirect(url_for("login"))


@app.route("/api/<string:book_isbn>")
def api_call(book_isbn):
    if not session["log"]:
        return render_template("404.html",message = "you have to login first for request")

    book = db.execute("select * from books WHERE isbn = :book_isbn ",
                      {"book_isbn": book_isbn}).fetchone()
    review = db.execute(
        "select COUNT(id) as review_count,AVG(rating) as average_rating from reviews WHERE book_isbn = :book_isbn ",
        {"book_isbn": book_isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid isbn no for book"}), 422
    if review is None:
        review["review_count"]=0;review["average_rating"]=0.0
    num = format(float(review["average_rating"]),".2f")
    return jsonify({
        "title":book["title"],
        "author":book["author"],
        "year":book["year"],
        "isbn": book["isbn"],
        "review count":review["review_count"],
        "average_score":num
    })




if __name__ == "__main__":
    app.run(debug=True)

