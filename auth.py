from flask import jsonify, request, redirect, session, Blueprint, current_app, flash, render_template
from .flask_indieauth import requires_indieauth
from .config import ME, CALLBACK_URL, CLIENT_ID
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

    r = requests.post(session.get("token_endpoint"), data=data, headers=headers)
    
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

    print(session)
        
    try:
        soup = BeautifulSoup(r.json().get("me"), "html.parser")
        mp_endpoint = soup.find("link", attrs={"rel": "micropub"})
        r = requests.get(mp_endpoint["href"] + "?q=config", headers={"Authorization": "Bearer " + r.json().get("access_token")})
        session["config"] = r.json()
        r = requests.get(mp_endpoint["href"] + "?q=syndicate-to", headers={"Authorization": "Bearer " + r.json().get("access_token")})
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

@auth.route("/discover", methods=["POST"])
def discover_auth_endpoint():
    domain = request.form.get("me")

    r = requests.get(domain)

    soup = BeautifulSoup(r.text, "html.parser")

    token_endpoint = soup.find("link", rel="token_endpoint")

    authorization_endpoint = soup.find("link", rel="authorization_endpoint")

    if token_endpoint is None:
        flash("An IndieAuth token endpoint could not be found on your website.")
        return redirect("/login")

    if not token_endpoint.get("href").startswith("https://") and not token_endpoint.get("href").startswith("http://"):
        flash("Your IndieAuth token endpoint published on your site must be a full HTTP URL.")
        return redirect("/login")

    if authorization_endpoint is None:
        flash("An IndieAuth authorization endpoint could not be found on your website.")
        return redirect("/login")

    if not authorization_endpoint.get("href").startswith("https://") and not authorization_endpoint.get("href").startswith("http://"):
        flash("Your IndieAuth authorization endpoint published on your site must be a full HTTP URL.")
        return redirect("/login")

    token_endpoint = token_endpoint["href"]

    session["token_endpoint"] = token_endpoint

    session["authorization_endpoint"] = authorization_endpoint["href"]

    random_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(30))

    session["code_verifier"] = random_code

    sha256_code = hashlib.sha256(random_code.encode('utf-8')).hexdigest()

    code_challenge = base64.b64encode(sha256_code.encode('utf-8')).decode('utf-8')

    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

    session["state"] = state

    return redirect(authorization_endpoint["href"] + "?client_id=" + CLIENT_ID + "&redirect_uri=" + CALLBACK_URL + "&scope=create update delete media undelete profile&response_type=code&code_challenge=" + code_challenge + "&code_challenge_method=S256&state=" + state)

@auth.route("/login", methods=["GET", "POST"])
def login():
    return render_template("auth.html", title="Micropub Dashboard Login")