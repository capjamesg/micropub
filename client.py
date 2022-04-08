import os

import indieweb_utils
import requests
from bs4 import BeautifulSoup
from flask import (Blueprint, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session)
from werkzeug.utils import secure_filename

from config import (CLIENT_ID, ENDPOINT_URL, MEDIA_ENDPOINT_URL,
                    TWITTER_BEARER_TOKEN, UPLOAD_FOLDER)

client = Blueprint("client", __name__, static_folder="static", static_url_path="")


@client.route("/", methods=["GET", "POST"])
def index():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        user = None
        me = None

    if request.method == "POST":
        if not user:
            abort(403)

        url = request.form["url"]

        if request.form["action"] == "update":
            return redirect(f"/update?url={url}")
        elif request.form["action"] == "delete":
            if session.get("scope") and not "delete" in session.get("scope").split(
                " "
            ):
                flash("You do not have permission to update posts.")
                return redirect("/")

            http_request = requests.post(
                ENDPOINT_URL,
                json={"type": ["h-entry"], "action": "delete", "url": url},
                headers={"Authorization": f"Bearer {user}"},
            )
            if http_request.status_code == 200 or http_request.status_code == 201:
                flash(f"Your {url} post was successfully deleted.")
            else:
                flash(http_request.json()["message"].strip("."))
            return render_template(
                "user/dashboard.html",
                user=user,
                me=me,
                title="WriteIt Home",
                action="delete",
            )
        elif request.form["action"] == "undelete":
            if session.get("scope") and not "undelete" in session.get(
                "scope"
            ).split(" "):
                flash("You do not have permission to undelete posts.")
                return redirect("/")

            http_request = requests.post(
                ENDPOINT_URL,
                json={"type": ["h-entry"], "action": "undelete", "url": url},
                headers={"Authorization": f"Bearer {user}"},
            )
            if http_request.status_code == 200 or http_request.status_code == 201:
                flash(f"Your {url} post was successfully undeleted.")
            else:
                flash(http_request.json()["message"].strip("."))
            return render_template(
                "user/dashboard.html",
                user=user,
                me=me,
                title="WriteIt Home",
                action="undelete",
            )

        return redirect("/")

    if user is not None:
        return render_template(
            "user/dashboard.html",
            user=user,
            me=me,
            title="WriteIt Dashboard",
            action=None,
        )
    else:
        return render_template(
            "index.html", user=user, me=me, title="Home WriteIt", action=None
        )


@client.route("/post", methods=["GET", "POST"])
def create_post():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")

    post_type = request.args.get("type")

    accepted_post_types = (
        ("like", "like-of"),
        ("repost", "repost-of"),
        ("bookmark", "bookmark-of"),
        ("rsvp", "rsvp"),
        ("reply", "in-reply-to"),
        ("checkin", ""),
        ("checkin", ""),
        ("photo", ""),
        ("watch", ""),
    )

    for item in accepted_post_types:
        post, attribute = item

        if post_type == post:
            title = f"Create a {post.title()} Post"
            url = request.args.get(attribute)

    if post_type == "photo" and "media" not in session.get("scope").split(" "):
        flash("You need to grant the 'media' scope to upload photos.")
        return redirect("/")

    if request.method == "POST":
        form_encoded = request.form.to_dict()

        if form_encoded.get("access_token"):
            del form_encoded["access_token"]

        if request.form.get("preview") and not request.form.get("in-reply-to"):
            post_type = None
            if request.form.get("like-of"):
                return redirect(
                    f"/post?type=like&like-of={request.form.get('like-of')}&is_previewing=true"
                )

            if request.form.get("bookmark-of"):
                return redirect(
                    f"/post?type=bookmark&bookmark-of={request.form.get('bookmark-of')}&is_previewing=true"
                )

            if request.form.get("repost-of"):
                return redirect(
                    f"/post?type=repost&repost-of={request.form.get('repost-of')}&is_previewing=true"
                )

        if me and user:
            data = {"type": ["h-entry"], "properties": {}}

            form_types = [
                "in-reply-to",
                "like-of",
                "repost-of",
                "bookmark-of",
                "watch-of",
            ]

            for key in form_encoded:
                if key in form_types:
                    del form_encoded["h"]
                    del form_encoded["action"]

                    data["properties"][key] = [form_encoded]
                    url = form_encoded[key]
                    break

            if (
                request.form.get("syndication")
                and request.form.get("syndication") != "none"
            ):
                data["syndication"] = [request.form.get("syndication")]

            if request.form.get("category") == "RSVP":
                data["p-rsvp"] = {}
                data["p-rsvp"]["properties"] = {
                    "event_name": request.form.get("event_name"),
                    "in-reply-to": request.form.get("in-reply-to"),
                    "state": request.form.get("state"),
                    "content": [request.form.get("content")],
                    "event_date": request.form.get("event_date"),
                    "event_time": request.form.get("event_time"),
                }
            elif request.form.get("venue_name"):
                data["properties"] = {"checkin": [{"properties": {}}]}

                data["properties"] = {
                    "checkin": [
                        {
                            "properties": {
                                "name": request.form.get("venue_name"),
                                "latitude": request.form.get("latitude"),
                                "longitude": request.form.get("longitude"),
                            }
                        }
                    ]
                }

                if request.form.get("content"):
                    data["properties"]["checkin"][0]["properties"]["content"] = [
                        request.form.get("content")
                    ]

                if (
                    not request.form.get("venue_name")
                    or not request.form.get("latitude")
                    or not request.form.get("longitude")
                ):
                    flash(
                        "Please enter a valid venue name, latitude, and longitude value."
                    )
                    return render_template(
                        "post/create_post.html",
                        title=title,
                        post_type=post_type,
                        user=user,
                        me=me,
                    )
            else:
                if request.form.get("title"):
                    data["properties"]["title"] = [request.form.get("title")]
                if request.form.get("content"):
                    data["properties"]["content"] = [request.form.get("content")]
                if request.form.get("category"):
                    data["properties"]["category"] = request.form.get("category").split(
                        ", "
                    )
                if request.form.get("is_hidden"):
                    data["properties"]["is_hidden"] = [request.form.get("is_hidden")]
                if (
                    request.form.get("content")
                    and BeautifulSoup(request.form.get("content"), "lxml")
                    and BeautifulSoup(request.form.get("content"), "lxml").find()
                ):
                    data["properties"]["content"] = [
                        {"html": request.form.get("content")}
                    ]
                elif (
                    request.form.get("content")
                    and request.form.get("content") is not None
                ):
                    data["properties"]["content"] = [request.form.get("content")]

            photo = request.files.get("photo")

            if photo:
                photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))

                # if session.get("config"):
                #     photo_r = requests.post(session["config"]["media-endpoint"], files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')}, headers={"Authorization": "Bearer " + user})
                # else:
                photo_http_request = requests.post(
                    MEDIA_ENDPOINT_URL,
                    files={
                        "file": (
                            secure_filename(photo.filename),
                            open(
                                os.path.join(
                                    UPLOAD_FOLDER, secure_filename(photo.filename)
                                ),
                                "rb",
                            ),
                            "image/jpeg",
                        )
                    },
                    headers={"Authorization": "Bearer " + user},
                )

                check_for_alt_text = False

                if photo:
                    data["properties"]["photo"] = [
                        {"value": photo_http_request.headers["Location"]}
                    ]
                    check_for_alt_text = True

                if check_for_alt_text and request.form.get("image_alt_text"):
                    data["properties"]["photo"][0]["alt"] = request.form.get(
                        "image_alt_text"
                    )

            if request.form.get("format") == "form_encoded":
                form_encoded["h"] = "entry"
                categories = []
                if (
                    form_encoded.get("category")
                    and len(form_encoded.get("category").split(", ")) > 0
                ):
                    for i in form_encoded.get("category").replace(", ", ",").split(","):
                        categories += [i]
                form_encoded["category[]"] = categories

                http_request = requests.post(
                    ENDPOINT_URL,
                    data=form_encoded,
                    headers={"Authorization": f"Bearer {user}"},
                )
            else:
                http_request = requests.post(
                    ENDPOINT_URL, json=data, headers={"Authorization": f"Bearer {user}"}
                )

            try:
                response = http_request.json()["message"]
            except:
                response = http_request.text

            if http_request.status_code != 200 and http_request.status_code != 201:
                flash("Error: " + str(response))

            if http_request.headers.get("Location"):
                return redirect(http_request.headers["Location"])

            flash("Your post was successfully created.")

            title = "Create Post"

            return render_template(
                "post/create_post.html",
                title=title,
                post_type=post_type,
                user=user,
                me=me,
            )

        return jsonify({"error": "You must be logged in to create a post."}), 401

    try:
        reply_context_response = indieweb_utils.get_reply_context(
            url, twitter_bearer_token=TWITTER_BEARER_TOKEN
        )

        h_entry = reply_context_response

        if reply_context_response.webmention_endpoint != "":
            site_supports_webmention = True
    except Exception:
        h_entry = None
        site_supports_webmention = False

    is_previewing = False

    if (
        request.args.get("is_previewing")
        and request.args.get("is_previewing") == "true"
    ):
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
        is_previewing=is_previewing,
    )


@client.route("/update", methods=["GET", "POST"])
def update_post():
    post_id = request.args.get("url")

    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")

    if session.get("scope") and not "update" in session.get("scope").split(" "):
        flash("You do not have permission to update posts.")
        return redirect("/")

    if "/checkin/" in post_id:
        post_type = "checkin"
    elif "/rsvp/" in post_id:
        post_type = "rsvp"
    elif "/webmentions/" in post_id:
        post_type = "reply"
    else:
        post_type = "note"

    try:
        properties = requests.get(
            ENDPOINT_URL + "?q=source&url=" + post_id,
            headers={"Authorization": f"Bearer {user}"},
        )

        properties = properties.json()
    except:
        abort(404)

    title = "Update a Post"

    if request.method == "POST":
        if me and user:
            data = {"action": "update", "url": post_id, "replace": {}}

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
                    "event_time": request.form.get("event_time"),
                }
            elif request.form.get("in-reply-to"):
                data["in-reply-to"] = request.form.get("in-reply-to")

            http_request = requests.post(
                ENDPOINT_URL,
                json=data,
                headers={
                    "Authorization": f"Bearer {user}",
                    "Content-Type": "application/json",
                },
            )

            try:
                response = http_request.json()

                if http_request.status_code != 200 and http_request.status_code != 201:
                    flash("Error: " + str(response["message"]))
                else:
                    return redirect(http_request.headers["Location"])
            except:
                flash("There was an unknown server errohttp_request.")

            return render_template(
                "post/update_post.html",
                title=title,
                post_type=post_type,
                user=user,
                me=me,
                id=post_id,
                properties=properties,
            )

        return jsonify({"error": "You must be logged in to create a post."}), 401

    return render_template(
        "post/update_post.html",
        title=title,
        post_type=post_type,
        user=user,
        me=me,
        id=id,
        properties=properties,
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

    client_id = CLIENT_ID.strip("/")

    return render_template(
        "user/settings.html",
        title="Settings",
        user=user,
        me=me,
        syndication=syndication,
        client_id=client_id,
    )


@client.route("/schemas")
def schemas():
    if session.get("access_token"):
        user = session["access_token"]
        me = session["me"]
    else:
        return redirect("/login")

    return render_template("user/schemas.html", title="Schemas", user=user, me=me)


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
        filename = secure_filename(request.form.get("filename").replace("..", ""))
    else:
        filename = secure_filename(photo.filename.replace("..", ""))

    photo.save(os.path.join(UPLOAD_FOLDER, filename))

    http_request = requests.post(
        MEDIA_ENDPOINT_URL,
        files={
            "file": (
                filename,
                open(os.path.join(UPLOAD_FOLDER, filename), "rb"),
                "image/jpeg",
            )
        },
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    if http_request.status_code != 201:
        flash("Error: " + str(http_request.json()["message"]))
        return redirect("/post?type=photo")

    location_header = http_request.headers["Location"]

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


@client.route("/manifest.json")
def web_app_manifest():
    return send_from_directory("static", "manifest.json")


@client.route("/emoji_autocomplete.js")
def emoji_autocomplete():
    return send_from_directory(client.static_folder, "js/emoji_autocomplete.js")
