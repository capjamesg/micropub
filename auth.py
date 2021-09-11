from flask import jsonify, request, redirect, session, Blueprint
from flask_micropub import MicropubClient
from bs4 import BeautifulSoup
from .config import *
import requests

auth = Blueprint("auth", __name__)

micropub = MicropubClient(auth, client_id=ENDPOINT_URL)

@auth.route("/login")
def login():
    scope = request.args.get("scope")
    if not scope:
        scope = "post create update delete undelete"
    return micropub.authorize("jamesg.blog", scope=scope, next_url=ENDPOINT_URL)

@auth.route("/logout")
def logout():
    session.pop("access_token", None)
    session.pop("me", None)
    return redirect("/")

@auth.route("/callback")
@micropub.authorized_handler
def micropub_callback(response):
    if response.error:
        return jsonify({"error": response.error})
    else:
        session["access_token"] = response.access_token
        session["me"] = response.me
        
        # try:
        #     soup = BeautifulSoup(r.text, "html.parser")
        #     mp_endpoint = soup.find("link", attrs={"rel": "micropub"})
        #     r = requests.get(mp_endpoint["href"] + "?q=config", headers={"Authorization": "Bearer " + response.access_token})
        #     session["config"] = r.json()
        #     r = requests.get(mp_endpoint["href"] + "?q=syndicate-to", headers={"Authorization": "Bearer " + response.access_token})
        #     session["syndication"] = r.json()
        # except:
        #     pass

    return redirect("/post")