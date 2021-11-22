from flask import request, render_template, redirect, session, Blueprint, flash, jsonify, abort, send_from_directory
from werkzeug.utils import secure_filename
from context import get_reply_context
from bs4 import BeautifulSoup
from github import Github
from config import *
import requests
import os

client = Blueprint("client", __name__, static_folder="static", static_url_path="")

g = Github(GITHUB_KEY)

@client.route("/", methods=["GET", "POST"])
def index():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        user = None
        me = None

    if request.method == "POST":
        if user:
            url = request.form["url"]
            if request.form["action"] == "update":
                return redirect("/update?url={}".format(url))
            elif request.form["action"] == "delete":
                if session.get("scopes") and not "delete" in session.get("scopes").split(" "):
                    flash("You do not have permission to update posts.")
                    return redirect("/")

                r = requests.post(ENDPOINT_URL,
                    json={"type": ["h-entry"], "action": "delete", "url": url},
                    headers={"Authorization": "Bearer {}".format(user)})
                if r.status_code == 200 or r.status_code == 201:
                    flash("Your {} post was successfully deleted.".format(url))
                else:
                    flash(r.json()["message"].strip("."))
                return render_template("user/dashboard.html", user=user, me=me, title="Home | Micropub Endpoint", action="delete")
            elif request.form["action"] == "undelete":
                if session.get("scopes") and not "undelete" in session.get("scopes").split(" "):
                    flash("You do not have permission to undelete posts.")
                    return redirect("/")
                r = requests.post(ENDPOINT_URL,
                    json={"type": ["h-entry"], "action": "undelete", "url": url},
                    headers={"Authorization": "Bearer {}".format(user)})
                if r.status_code == 200 or r.status_code == 201:
                    flash("Your {} post was successfully undeleted.".format(url))
                else:
                    flash(r.json()["message"].strip("."))
                return render_template("user/dashboard.html", user=user, me=me, title="Home | Micropub Endpoint", action="undelete")
            else:
                return redirect("/")
        else:
            abort(403)

    if user != None:
        return render_template("user/dashboard.html", user=user, me=me, title="Dashboard | Micropub Endpoint", action=None)
    else:
        return render_template("index.html", user=user, me=me, title="Home | Micropub Endpoint", action=None)

@client.route("/post", methods=["GET", "POST"])
def create_post():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")

    post_type = request.args.get("type")

    if post_type == "coffee":
        title = "Create a Coffee Post"
        url = None
        request_type = None
    elif post_type == "note":
        title = "Create a Note"
        url = None
        request_type = None
    elif post_type == "like":
        title = "Create a Like"
        url = request.args.get("like-of")
        request_type = "like-of"
    elif post_type == "repost":
        title = "Create a Repost"
        url = request.args.get("repost-of")
        request_type = "repost-of"
    elif post_type == "rsvp":
        title = "Create a RSVP"
        url = request.args.get("rsvp")
        request_type = None
    elif post_type == "bookmark":
        title = "Create a Bookmark"
        url = request.args.get("bookmark")
        request_type = "bookmark-of"
    elif post_type == "checkin":
        title = "Create a checkin"
        url = None
        request_type = None
    elif post_type == "photo":
        title = "Upload a Photo"
        url = None
        request_type = None
        if session.get("scope") and "media" not in session.get("scope").split(" "):
            flash("You need to grant the 'media' scope to upload photos.")
            return redirect("/")
    else:
        title = "Create a Reply"
        url = request.args.get("in-reply-to")
        request_type = "in-reply-to"

    if request.method == "POST":
        form_encoded = request.form.to_dict()

        if form_encoded.get("access_token"):
            del form_encoded["access_token"]

        if request.form.get("preview") and not request.form.get("in-reply-to"):
            post_type = None
            if request.form.get("like-of"):
                return redirect("/post?type=like&like-of={}&is_previewing=true".format(request.form.get("like-of")))
            elif request.form.get("bookmark-of"):
                return redirect("/post?type=bookmark&bookmark-of={}&is_previewing=true".format(request.form.get("bookmark-of")))
            elif request.form.get("repost-of"):
                return redirect("/post?type=repost&repost-of={}&is_previewing=true".format(request.form.get("repost-of")))

        if me and user:
            data = {
                "type": ["h-entry"],
            }
            
            if request.form.get("in-reply-to"):
                data["in-reply-to"] = [request.form.get("in-reply-to")]
                url = request.form.get("in-reply-to")
                request_type = "in-reply-to"
            
            if request.form.get("like-of"):
                data["like-of"] = [request.form.get("like-of")]
                url = request.form.get("like-of")
                request_type = "like-of"
            
            if request.form.get("repost-of"):
                data["repost-of"] = [request.form.get("repost-of")]
                url = request.form.get("repost-of")
                request_type = "repost-of"
            
            if request.form.get("bookmark-of"):
                data["bookmark-of"] = [request.form.get("bookmark-of")]
                url = request.form.get("bookmark-of")
                request_type = "bookmark-of"

            if request.form.get("syndication") and request.form.get("syndication") != "none":
                data["syndication"] = [request.form.get("syndication")]

            data["properties"] = {}

            # if roaster or varietals or country
            if request.form.get("drank"):
                data["drank"] = [{
                        "properties": {
                            "title": [request.form.get("title")],
                            "content": [request.form.get("content")],
                            "category": request.form.get("category").split(", ")
                        }
                    }]
                data["drank"][0]["properties"]["coffee_info"] = {}
                if request.form.get("content") and BeautifulSoup(request.form.get("content"), "lxml") and BeautifulSoup(request.form.get("content"), "lxml").find():
                    data["drank"][0]["properties"]["content"] = [{"html": request.form.get("content")}]
            elif request.form.get("category") == "RSVP":
                data["p-rsvp"] = {}
                data["p-rsvp"]["properties"] = {
                    "event_name": request.form.get("event_name"),
                    "in-reply-to": request.form.get("in-reply-to"),
                    "state": request.form.get("state"), 
                    "content": [request.form.get("content")], 
                    "event_date": request.form.get("event_date"), 
                    "event_time": request.form.get("event_time")
                }
            elif request.form.get("venue_name"):
                data["properties"] = {"checkin": [{"properties": {}}]}
                data["properties"]["checkin"][0]["properties"]["name"] = [request.form.get("venue_name")]
                data["properties"]["checkin"][0]["properties"]["latitude"] = [request.form.get("latitude")]
                data["properties"]["checkin"][0]["properties"]["longitude"] = [request.form.get("longitude")]
                if request.form.get("content"):
                    data["properties"]["checkin"][0]["properties"]["content"] = [request.form.get("content")]

                if not request.form.get("venue_name") or not request.form.get("latitude") or not request.form.get("longitude"):
                    flash("Please enter a valid venue name, latitude, and longitude value.")
                    return render_template("post/create_post.html", title=title, post_type=post_type, user=user, me=me)
            else:
                if request.form.get("title"):
                    data["properties"]["title"] = [request.form.get("title")]
                if request.form.get("content"):
                    data["properties"]["content"] = [request.form.get("content")]
                if request.form.get("category"):
                    data["properties"]["category"] = request.form.get("category").split(", ")
                if request.form.get("is_hidden"):
                    data["properties"]["is_hidden"] = [request.form.get("is_hidden")]
                if request.form.get("content") and BeautifulSoup(request.form.get("content"), "lxml") and BeautifulSoup(request.form.get("content"), "lxml").find():
                    data["properties"]["content"] = [{"html": request.form.get("content")}]
                elif request.form.get("content") and request.form.get("content") != None:
                    data["properties"]["content"] = [request.form.get("content")]

            coffee_info_properties = ["roaster", "varietals", "country", "process"]

            for prop in coffee_info_properties:
                if request.form.get(prop):
                    data["drank"][0]["properties"]["coffee_info"][prop] = [request.form.get(prop)]

            photo = request.files.get("photo")

            if photo:
                photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))

                # if session.get("config"):
                #     photo_r = requests.post(session["config"]["media-endpoint"], files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')}, headers={"Authorization": "Bearer " + user})
                # else:
                photo_r = requests.post(MEDIA_ENDPOINT_URL,
                    files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')},
                    headers={"Authorization": "Bearer " + user})

                check_for_alt_text = False

                if photo and not request.form.get("drank"):
                    data["properties"]["photo"] = [{ "value": photo_r.headers["Location"] }]
                    check_for_alt_text = True
                elif photo and request.form.get("drank"):
                    data["drank"][0]["properties"]["photo"] = [{ "value": photo_r.headers["Location"] }]
                    check_for_alt_text = True

                if check_for_alt_text and request.form.get("image_alt_text") and not request.form.get("drank"):
                    data["properties"]["photo"][0]["alt"] = request.form.get("image_alt_text")
                elif check_for_alt_text and request.form.get("image_alt_text") and request.form.get("drank"):
                    data["drank"][0]["properties"]["photo"][0]["alt"] = request.form.get("image_alt_text")

            if request.form.get("format") == "form_encoded":
                form_encoded["h"] = "entry"
                categories = []
                if form_encoded.get("category") and len(form_encoded.get("category").split(", ")) > 0:
                    for i in form_encoded.get("category").replace(", ", ",").split(","):
                        categories += [i]
                form_encoded["category[]"] = categories

                r = requests.post(ENDPOINT_URL, data=form_encoded, headers={"Authorization": "Bearer {}".format(user)})
            else:
                r = requests.post(ENDPOINT_URL, json=data, headers={"Authorization": "Bearer {}".format(user)})

            try:
                response = r.json()
            except:
                response = r.text

            if r.status_code != 200 and r.status_code != 201:
                flash("Error: " + str(response["message"]))
            elif r.headers.get("Location"):
                return redirect(r.headers["Location"])
            else:
                flash("Your post was successfully created.")
            
            return render_template("post/create_post.html", title=title, post_type=post_type, user=user, me=me)
        else:
            return jsonify({"error": "You must be logged in to create a post."}), 401

    if request_type != None and url:
        h_entry, site_supports_webmention = get_reply_context(url, request_type)
    else:
        h_entry = None
        site_supports_webmention = False

    is_previewing = False

    if request.args.get("is_previewing") and request.args.get("is_previewing") == "true":
        is_previewing = True

    return render_template(
        "post/create_post.html",
        title=title,
        post_type=post_type,
        user=user,
        me=me,
        url=url,
        h_entry=h_entry,
        site_supports_webmention=site_supports_webmention,
        is_previewing=is_previewing
    )

@client.route("/update", methods=["GET", "POST"])
def update_post():
    id = request.args.get("url")

    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")

    if session.get("scopes") and not "update" in session.get("scopes").split(" "):
        flash("You do not have permission to update posts.")
        return redirect("/")

    if "/checkin/" in id:
        post_type = "checkin"
    elif "/coffee/" in id:
        post_type = "coffee"
    elif "/rsvp/" in id:
        post_type = "rsvp"
    elif "/webmentions/" in id:
        post_type = "reply"
    else:
        post_type = "note"

    try:
        properties = requests.get(ENDPOINT_URL + "?q=source&url=" + id,
            headers={"Authorization": "Bearer {}".format(user)})

        properties = properties.json()
    except:
        abort(404)

    title = "Update a Post"

    if request.method == "POST":
        if me and user:
            data = {
                "action": "update",
                "url": id,
                "replace": {}
            }

            if request.form.get("title"):
                data["replace"]["title"] = [request.form.get("title")]
            else:
                data["replace"]["title"] = ""
            if request.form.get("content"):
                data["replace"]["content"] = [request.form.get("content")]
            else:
                data["replace"]["content"] = []
            if request.form.get("image_alt_text"):
                data["replace"]["image_alt_text"] = request.form.get("image_alt_text")
            else:
                data["replace"]["image_alt_text"] = ""
            if request.form.get("category"):
                data["replace"]["category"] = request.form.get("category")

            if request.form.get("is_hidden"):
                data["replace"]["is_hidden"] = [request.form.get("is_hidden")]

            if post_type == "rsvp":
                data["p-rsvp"] = {}
                data["p-rsvp"]["properties"] = {
                    "in-reply-to": properties["properties"]["in-reply-to"],
                    "rsvp": request.form.get("rsvp"),
                    "state": request.form.get("state"),
                    "content": [request.form.get("content")],
                    "event_date": request.form.get("event_date"),
                    "event_time": request.form.get("event_time")
                }
            elif request.form.get("in-reply-to"):
                data["in-reply-to"] = request.form.get("in-reply-to")

            r = requests.post(ENDPOINT_URL, json=data, headers={
                "Authorization": "Bearer {}".format(user), "Content-Type": "application/json"
            })

            try:
                response = r.json()

                if r.status_code != 200 and r.status_code != 201:
                    flash("Error: " + str(response["message"]))
                else:
                    return redirect(r.headers["Location"])
            except:
                flash("There was an unknown server error.")
            
            return render_template(
                "post/update_post.html",
                title=title,
                post_type=post_type,
                user=user, me=me,
                id=id,
                properties=properties
            )
        else:
            return jsonify({"error": "You must be logged in to create a post."}), 401

    return render_template(
            "post/update_post.html",
            title=title,
            post_type=post_type,
            user=user, me=me,
            id=id,
            properties=properties
        )

@client.route("/settings")
def settings():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
        if session.get("syndication"):
            syndication = session["syndication"]
        else:
            syndication = None
    else:
        return redirect("/login")
    
    return render_template("user/settings.html", title="Settings | Micropub Endpoint", user=user, me=me, syndication=syndication)

@client.route("/schemas")
def schemas():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")
    
    return render_template("user/schemas.html", title="Schemas | Micropub Endpoint", user=user, me=me)

# use this to forward client-side uploads from /post?type=photo to the /media micropub endpoint
@client.route("/media-forward", methods=["POST"])
def forward_media_query():
    if not session.get("access_token"):
        return redirect("/login")

    photo = request.files.get("photo")

    if not photo:
        flash("No photo was uploaded. Please upload a photo and try again.")
        return redirect("/post?type=photo")

    if not session.get("access_token"):
        return jsonify({"error": "You must be logged in to upload a photo."}), 401
    
    if request.form.get("filename"):
        filename = secure_filename(request.form.get("filename").replace(".", ""))
    else:
        filename = secure_filename(photo.filename.replace(".", ""))

    photo.save(os.path.join(UPLOAD_FOLDER, filename))

    r = requests.post(MEDIA_ENDPOINT_URL,
        files={"file": (filename,open(os.path.join(UPLOAD_FOLDER, filename), "rb"), 'image/jpeg')},
        headers={"Authorization": "Bearer {}".format(session["access_token"])})

    if r.status_code != 201:
        flash("Error: " + str(r.json()["message"]))
        return redirect("/post?type=photo")

    location_header = r.headers["Location"]

    return redirect(location_header)

@client.route("/robots.txt")
def robots():
    return send_from_directory(client.static_folder, "robots.txt")

@client.route("/favicon.ico")
def favicon():
    return send_from_directory(client.static_folder, "favicon.ico")

@client.route("/emojis.json")
def emojis():
    return send_from_directory(client.static_folder, "emojis.json")

@client.route("/emoji_autocomplete.js")
def emoji_autocomplete():
    return send_from_directory(client.static_folder, "js/emoji_autocomplete.js")