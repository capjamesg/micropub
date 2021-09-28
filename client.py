from flask import request, render_template, redirect, session, Blueprint, flash, jsonify, abort
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from github import Github
from .config import *
import requests
import mf2py
import os

client = Blueprint("client", __name__)

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
                return redirect("/update/?url={}".format(url))
            elif request.form["action"] == "delete":
                r = requests.post(ENDPOINT_URL, json={"type": ["h-entry"], "action": "delete", "url": url}, headers={"Authorization": "Bearer {}".format(user)})
                if r.status_code == 200 or r.status_code == 201:
                    flash("Your {} post was successfully deleted.".format(url))
                else:
                    flash(r.json()["message"].strip("."))
                return render_template("index.html", user=user, me=me, title="Home | Micropub Endpoint", action="delete")
            elif request.form["action"] == "undelete":
                r = requests.post(ENDPOINT_URL, json={"type": ["h-entry"], "action": "undelete", "url": url}, headers={"Authorization": "Bearer {}".format(user)})
                if r.status_code == 200 or r.status_code == 201:
                    flash("Your {} post was successfully undeleted.".format(url))
                else:
                    flash(r.json()["message"].strip("."))
                return render_template("index.html", user=user, me=me, title="Home | Micropub Endpoint", action="undelete")
            else:
                return redirect("/")
        else:
            abort(403)
    return render_template("index.html", user=user, me=me, title="Home | Micropub Endpoint", action=None)

@client.route("/post", methods=["GET", "POST"])
def create_post():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login?scope=post, create, update, delete, undelete")

    post_type = request.args.get("type")

    if post_type == "coffee":
        title = "Create a Coffee Post"
        url = None
    elif post_type == "note":
        title = "Create a Note"
        url = None
    elif post_type == "like":
        title = "Create a Like"
        url = request.args.get("like-of")
    elif post_type == "repost":
        title = "Create a Repost"
        url = request.args.get("repost-of")
    elif post_type == "rsvp":
        title = "Create a RSVP"
        url = request.args.get("rsvp")
    elif post_type == "bookmark":
        title = "Create a Bookmark"
        url = request.args.get("bookmark")
    elif post_type == "checkin":
        title = "Create a checkin"
        url = None
    else:
        title = "Create a Reply"
        url = request.args.get("in-reply-to")

    if request.args.get("like-of") or request.args.get("in-reply-to") or request.args.get("repost-of") or request.args.get("bookmark") and (url.startswith("https://") or url.startswith("http://")):
        parsed = mf2py.parse(requests.get(url).text)

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        if parsed["items"] and parsed["items"][0]["type"] == "h-entry":
            h_entry = parsed["items"][0]

            if h_entry["properties"].get("author"):
                author_url = h_entry['properties']['author'][0]['properties']['url'][0] if h_entry['properties']['author'][0]['properties'].get('url') else None
                author_name = h_entry['properties']['author'][0]['properties']['name'][0] if h_entry['properties']['author'][0]['properties'].get('name') else None
                author_image = h_entry['properties']['author'][0]['properties']['image'][0] if h_entry['properties']['author'][0]['properties'].get('image') else None
            else:
                author_url = None
                author_name = None
                author_image = None

            if h_entry["properties"].get("content") and h_entry["properties"].get("content")[0].get("html"):
                post_body = h_entry["properties"]["content"][0]["html"]
            elif h_entry["properties"].get("content"):
                post_body = h_entry["properties"]["content"]
            else:
                post_body = None

            # get p-name
            if h_entry["properties"].get("p-name"):
                p_name = h_entry["properties"]["p-name"][0]
            else:
                p_name = None

            h_entry = {"author_image": author_image, "author_url": author_url, "author_name": author_name, "post_body": post_body, "p-name": p_name}
        else:
            h_entry = {}
            try:
                soup = BeautifulSoup(requests.get(url).text, "html.parser")

                page_title = soup.title.string

                # get main tag
                main_tag = soup.find("main")

                if main_tag:
                    p_tag = main_tag.find("p").text
                else:
                    p_tag = None

                if soup.select('.e-content'):
                    p_tag = soup.select('.e-content')[0].text
                    p_tag = " ".join([w for w in p_tag.split(" ")[:75]])
                    
                favicon = soup.find("link", rel="icon")

                if favicon:
                    photo_url = favicon["href"]
                    if not photo_url.startswith("https://") or not photo_url.startswith("http://"):
                        photo_url = "https://" + domain + photo_url
                else:
                    photo_url = None

                h_entry = {"p-name": page_title, "post_body": p_tag, "author_image": photo_url, "author_url": domain, "author_name": domain}
            except:
                pass

            try:
                #if parsed["items"] and parsed["items"][0]["type"] == "h-entry":
                if parsed["items"][0]["properties"].get("photo"):
                    photo_url = parsed["items"][0]["properties"]["photo"][0]
                    if not photo_url.startswith("https://") or not photo_url.startswith("http://"):
                        photo_url = "https://" + domain + photo_url

                if len(parsed["items"]) > 0:
                    if parsed["items"][0]["properties"].get("photo"):
                        author_name = parsed["items"][0]["properties"]["name"][0]
                    else:
                        author_name = h_entry["author_name"]

                    if parsed["items"][0]["properties"].get("url"):
                        author_url = parsed["items"][0]["properties"]["url"][0]
                    else:
                        author_url = h_entry["author_url"]

                h_entry = {"author_image": photo_url, "author_url": author_url, "author_name": author_name, "post_body": p_tag, "p-name": page_title}
            except:
                pass
    else:
        h_entry = None

    if request.method == "POST":
        form_encoded = request.form.to_dict()
        if form_encoded.get("access_token"):
            del form_encoded["access_token"]

        if me and user:
            data = {
                "type": ["h-entry"],
            }
            
            if request.form.get("in-reply-to"):
                data["in-reply-to"] = [request.form.get("in-reply-to")]
            
            if request.form.get("like-of"):
                data["like-of"] = [request.form.get("like-of")]
            
            if request.form.get("repost-of"):
                data["repost-of"] = [request.form.get("repost-of")]
            
            if request.form.get("bookmark-of"):
                data["bookmark-of"] = [request.form.get("bookmark-of")]

            if request.form.get("syndication") and request.form.get("syndication") != "none":
                data["syndication"] = [request.form.get("syndication")]

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
                data["p-rsvp"]["properties"] = {"event_name": request.form.get("event_name"), "in-reply-to": request.form.get("in-reply-to"), "state": request.form.get("state"), "content": [request.form.get("content")], "event_date": request.form.get("event_date"), "event_time": request.form.get("event_time")}
            elif request.form.get("venue_name"):
                data["properties"] = {"checkin": [{"properties": {}}]}
                data["properties"]["checkin"][0]["properties"]["name"] = [request.form.get("venue_name")]
                data["properties"]["checkin"][0]["properties"]["latitude"] = [request.form.get("latitude")]
                data["properties"]["checkin"][0]["properties"]["longitude"] = [request.form.get("longitude")]
                if request.form.get("content"):
                    data["properties"]["checkin"][0]["properties"]["content"] = [request.form.get("content")]

                if not request.form.get("venue_name") or not request.form.get("latitude") or not request.form.get("longitude"):
                    flash("Please enter a valid venue name, latitude, and longitude value.")
                    return render_template("create_post.html", title=title, post_type=post_type, user=user, me=me)
            else:
                data["properties"] = {}
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

            if request.form.get("roaster"):
                data["drank"][0]["properties"]["coffee_info"]["roaster"] = [request.form.get("roaster")]

            if request.form.get("varietals"):
                data["drank"][0]["properties"]["coffee_info"]["varietals"] = [request.form.get("varietals")]

            if request.form.get("country"):
                data["drank"][0]["properties"]["coffee_info"]["country"] = [request.form.get("country")]

            if request.form.get("process"):
                data["drank"][0]["properties"]["coffee_info"]["process"] = [request.form.get("process")]

            photo = request.files.get("photo")

            if photo:
                photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))

                # if session.get("config"):
                #     photo_r = requests.post(session["config"]["media-endpoint"], files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')}, headers={"Authorization": "Bearer " + user})
                # else:
                photo_r = requests.post(MEDIA_ENDPOINT_URL, files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')})

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

            print(data)

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
            
            return render_template("create_post.html", title=title, post_type=post_type, user=user, me=me)
        else:
            return jsonify({"error": "You must be logged in to create a post."}), 401

    return render_template("create_post.html", title=title, post_type=post_type, user=user, me=me, url=url, h_entry=h_entry)

@client.route("/update/", methods=["GET", "POST"])
def update_post():
    id = request.args.get("url")
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login?scope=post, create, update, delete, undelete")

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
        properties = requests.get(ENDPOINT_URL + "?q=source&url=" + id, headers={"Authorization": "Bearer {}".format(user)})

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
            else:
                category = ""
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

            r = requests.post(ENDPOINT_URL, json=data, headers={"Authorization": "Bearer {}".format(user), "Content-Type": "application/json"})

            try:
                response = r.json()

                if r.status_code != 200 and r.status_code != 201:
                    flash("Error: " + str(response["message"]))
                else:
                    return redirect(r.headers["Location"])
            except:
                flash("There was an unknown server error.")
            
            return render_template("update_post.html", title=title, post_type=post_type, user=user, me=me, id=id, properties=properties)
        else:
            return jsonify({"error": "You must be logged in to create a post."}), 401

    return render_template("update_post.html", title=title, post_type=post_type, user=user, me=me, id=id, properties=properties)

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
        return redirect("/login?scope=post, create, update, delete, undelete")
    
    return render_template("settings.html", title="Settings | Micropub Endpoint", user=user, me=me, syndication=syndication)

@client.route("/schemas")
def schemas():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login?scope=post, create, update, delete, undelete")
    
    return render_template("schemas.html", title="Schemas | Micropub Endpoint", user=user, me=me)