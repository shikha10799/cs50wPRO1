import os
import requests
import datetime

from flask import Flask, render_template, request,jsonify,flash,redirect,session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt
from password_strength import PasswordPolicy
from decorators import login_required
app = Flask(__name__, static_url_path='/static')

#Check for environment variable
#if not os.getenv("DATABASE_URL"):
   #raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(process.env.DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))


policy = PasswordPolicy.from_names(
    length=8,  # min length: 8
    uppercase=1,  # need min. 2 uppercase letters
    numbers=1,  # need min. 2 digits
    special=1,  # need min. 2 special characters
)

@app.route("/")
def index():
    # our home page
    return render_template('index.html')

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method == "POST" :

        username = request.form.get("username")
        password = request.form.get("password")

        if not (username and password):
            flash("error","Please enter all the fields")
            return redirect("/register")

        elif session and session["user_name"] == username:
            flash("error","You are already logged in")
            return redirect("/")
        else:
            fetch = db.execute("select userid,name,username,password from users where username = :username",{"username":username}).fetchone()

            if fetch and sha256_crypt.verify(password,fetch["password"]):

                session["user_name"]=username
                session["user_id"]=fetch["userid"]
                session["name"]=fetch["name"]

                flash("success","You were successfully logged in.")
                return redirect("/")
            else:
                flash("error","Inavalid Username/Password")
                return redirect("/login")


    else:
        return render_template('login.html')

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()
    flash("success","You were successfully logged out.")
    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """ Register user """
    if request.method =='POST':
        name=request.form.get("name")
        username=request.form.get("username")
        password=request.form.get("password")
        confirm=request.form.get("confirm")
        # Forget any user_id

        if not (name and username and password and confirm) :
            flash("error","Please enter all the fields!!")
            return redirect("/register")
        else:
            check = db.execute("select * from users where username=:username",{"username":username}).fetchone()

            if check:
                flash("error","Username already exists")
                return redirect("/register")
            elif not password==confirm :
                flash("error","The passwords don\'t match")
                return redirect("/register")
            elif policy.test(password):
                flash("error","The password should have minimum length 8, atleast one uppercase, a number and a special symbol")
                return redirect("/register")
            else:
                hash = sha256_crypt.encrypt(password)
                db.execute("insert into users(name,username,password) values (:name,:username,:hash)",{"name":name,"username":username,"hash":hash})
                db.commit()
                flash("success","You were successfully registered")
                return redirect("/")
            # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/searchpage",methods=["GET"])
@login_required
def searchpage():
    return render_template("findbooks.html")


@app.route("/search",methods=["GET"])
@login_required
def search():

    book = request.args.get("book")
    if not book:
        flash("error","Please provide an input")
        return render_template("findbooks.html")

    book = "%" + book + "%"
    rows = db.execute("SELECT isbn,title,author,pubyr FROM books WHERE \
                        isbn LIKE :query OR \
                        title LIKE :query OR \
                        author LIKE :query",
                        {"query": book})

    if rows.rowcount == 0:
        flash("error","we can't find books with that description.")
        return render_template("findbooks.html")

    # Fetch all the results
    books = rows.fetchall()

    return render_template("findbooks.html",books=books)


@app.route("/search/<isbn>",methods=['GET','POST'])
@login_required
def bookinfo(isbn):
    if request.method == 'GET' :

        bookdetails = db.execute("select bookid,isbn,title,author,pubyr from books where isbn=:isbn",{"isbn":isbn}).fetchone()

        reviews = db.execute("select users.name as name,review as text,time as time,rating as rating from users inner join reviews on users.userid=reviews.userid where reviews.bookid=:bookid",{"bookid":bookdetails["bookid"]})
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":os.getenv("API_KEY"), "isbns":isbn})
        goodreads_data = res.json()
        goodreads_data = goodreads_data['books'][0]
        return render_template("results.html",bookdetails=bookdetails,reviews=reviews,goodreads_data=goodreads_data)

    if request.method == 'POST':
        review = request.form.get("review")
        rating = request.form.get("rating")
        if not (review and rating) :
            flash("error","Please enter all the fields.")
            return redirect("/search/" + isbn)
        try:
            if (int(rating) < 1) or int(rating) > 5 :
                flash("error","please enter valid field values")
                return redirect("/search/" + isbn)
        except:
                flash("error","please enter valid field values")
                return redirect("/search/" + isbn)
        book_id = db.execute("select bookid from books where isbn=:isbn",{"isbn":isbn}).fetchone()
        book_id =book_id["bookid"]
        reviewrecord = db.execute("select * from reviews where userid=:userid and bookid = :bookid",{"userid":session["user_id"],"bookid":book_id}).fetchone()
        if reviewrecord :
            flash("error","You cannot submit more than one review.")
            return redirect("/search/" + isbn)
        current_time = datetime.datetime.now()
        db.execute("insert into reviews(userid,bookid,review,rating,time) values (:userid,:bookid,:review,:rating,:time)",{"userid":session["user_id"],"bookid":book_id,"review":review,"rating":rating ,"time":current_time})
        db.commit()
        flash("success"," Succesfully submitted review")
        return redirect("/search/" + isbn)

@app.route("/api", methods=['GET','POST'])
@login_required
def api():
    if request.method == "POST":
        isbn = request.form.get("isbn")
        isbn = isbn.strip()
        return redirect("/api/"+isbn)
    else:
        return render_template("api.html")

@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):

    # COUNT returns rowcount
    # SUM returns sum selected cells' values
    # INNER JOIN associates books with reviews tables

    row = db.execute("SELECT title, author, pubyr, isbn from books where isbn = :isbn",{"isbn":isbn}).fetchone()

    if not row:
        return jsonify({"Error": "ISBN not found"}), 404

    dict = {"title":row["title"],"author":row["author"],"year":row["pubyr"],"isbn":row["isbn"]}

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":os.getenv("API_KEY"), "isbns":isbn})
    goodreads_data = res.json()
    goodreads_data = goodreads_data['books'][0]


    review_count = goodreads_data["work_ratings_count"]
    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    average_score = float('%.1f'%(float(goodreads_data["average_rating"])))

    dict.update({"review_count":review_count,"average_score":average_score})

    return jsonify(dict)
