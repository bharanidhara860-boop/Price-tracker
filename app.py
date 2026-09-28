import json
import os
import threading
import time

from flask import Flask, render_template, request, redirect, url_for, session, flash

import config
import otp_service
from scraper import scrape_product
from notifier import notify_price_drop

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

DATA_FILE = os.path.join(os.path.dirname(__file__), "products.json")
_lock = threading.Lock()


def load_products():
    with _lock:
        with open(DATA_FILE, "r") as f:
            return json.load(f)


def save_products(products):
    with _lock:
        with open(DATA_FILE, "w") as f:
            json.dump(products, f, indent=2)


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("mobile_number"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form["mobile_number"].strip()
        otp_service.generate_otp(mobile)
        session["pending_mobile"] = mobile
        flash("OTP sent (check console/email depending on OTP_MODE in config.py)")
        return redirect(url_for("verify"))
    return render_template("login.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    mobile = session.get("pending_mobile")
    if not mobile:
        return redirect(url_for("login"))
    if request.method == "POST":
        otp = request.form["otp"].strip()
        if otp_service.verify_otp(mobile, otp):
            session["mobile_number"] = mobile
            session.pop("pending_mobile", None)
            return redirect(url_for("dashboard"))
        flash("Invalid or expired OTP, try again.")
    return render_template("verify.html", mobile=mobile)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    products = load_products()
    return render_template("dashboard.html", products=products)


@app.route("/add", methods=["POST"])
@login_required
def add_product():
    url = request.form["url"].strip()
    try:
        info = scrape_product(url)
    except Exception as e:
        flash(f"Couldn't fetch that product: {e}")
        return redirect(url_for("dashboard"))

    if info is None:
        flash("Price not found on that page (site layout may have changed).")
        return redirect(url_for("dashboard"))

    products = load_products()
    products.append(
        {
            "url": url,
            "title": info["title"],
            "current_price": info["price"],
            "lowest_price": info["price"],
        }
    )
    save_products(products)
    flash(f"Added: {info['title']}")
    return redirect(url_for("dashboard"))


@app.route("/remove/<int:index>", methods=["POST"])
@login_required
def remove_product(index):
    products = load_products()
    if 0 <= index < len(products):
        products.pop(index)
        save_products(products)
    return redirect(url_for("dashboard"))


@app.route("/check-now", methods=["POST"])
@login_required
def check_now():
    check_all_prices()
    flash("Checked all tracked products.")
    return redirect(url_for("dashboard"))


def check_all_prices():
    products = load_products()
    changed = False
    for p in products:
        try:
            info = scrape_product(p["url"])
        except Exception:
            continue
        if info is None:
            continue

        new_price = info["price"]
        old_price = p["current_price"]

        if new_price < old_price:
            notify_price_drop(p["title"], old_price, new_price, p["url"])

        p["current_price"] = new_price
        p["lowest_price"] = min(p.get("lowest_price", new_price), new_price)
        changed = True

    if changed:
        save_products(products)


def background_loop():
    interval = getattr(config, "CHECK_INTERVAL_MINUTES", 30) * 60
    while True:
        time.sleep(interval)
        try:
            check_all_prices()
        except Exception as e:
            print(f"[background check error] {e}")


if __name__ == "__main__":
    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    app.run(debug=True)
