from functools import wraps
from flask import session, request, redirect, url_for,flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            flash("error","Kindly Login to access the page !!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
