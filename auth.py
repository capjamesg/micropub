from flask import jsonify, request, redirect, session, Blueprint, current_app, flash, render_template
from .flask_indieauth import requires_indieauth
from .config import ME, TOKEN_ENDPOINT, CALLBACK_URL, CLIENT_ID, ENDPOINT_URL
from bs4 import BeautifulSoup
import requests
import random
import string
import hashlib
import base64

auth = Blueprint("auth", __name__)

@auth.route("/callback")
def indieauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if state != session.get("state"):
        flash("Your authentication failed. Please try again.")
        return redirect("/")

    data = {
        "code": code,
        "redirect_uri": CALLBACK_URL,
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code_verifier": session["code_verifier"]
    }

    headers = {
        "Accept": "application/json"
    }

    r = requests.post(TOKEN_ENDPOINT, data=data, headers=headers)
    
    if r.status_code != 200:
        flash("There was an error with your token endpoint server.")
        return redirect("/login")

    # remove code verifier from session because the authentication flow has finished
    session.pop("code_verifier")

    if r.json().get("me").strip("/") != ME.strip("/"):
        flash("Your domain is not allowed to access this website.")
        return redirect("/login")

    session["me"] = r.json().get("me")
    session["access_token"] = r.json().get("access_token")
        
    try:
        soup = BeautifulSoup(r.json().get("me"), "html.parser")
        mp_endpoint = soup.find("link", attrs={"rel": "micropub"})
        r = requests.get(mp_endpoint["href"] + "?q=config", headers={"Authorization": "Bearer " + response.access_token})
        session["config"] = r.json()
        r = requests.get(mp_endpoint["href"] + "?q=syndicate-to", headers={"Authorization": "Bearer " + response.access_token})
        session["syndication"] = r.json()
    except:
        pass

    return redirect("/")

@auth.route("/logout")
@requires_indieauth
def logout():
    session.pop("me")
    session.pop("access_token")

    return redirect("/home")

@auth.route("/login", methods=["GET", "POST"])
def login():
    random_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(30))

    session["code_verifier"] = random_code

    sha256_code = hashlib.sha256(random_code.encode('utf-8')).hexdigest()

    code_challenge = base64.b64encode(sha256_code.encode('utf-8')).decode('utf-8')

    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

    session["state"] = state

    return render_template("auth.html", title="Webmention Dashboard Login", code_challenge=code_challenge, state=state)