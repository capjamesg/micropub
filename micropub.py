from flask import jsonify, request, session, g, Blueprint, abort
from werkzeug.utils import secure_filename
from .flask_indieauth import requires_indieauth
from github import Github
from PIL import Image, ImageOps
from . import create_items
from .config import *
import requests
import string
import random
import yaml
import os

micropub = Blueprint("micropub", __name__)

g = Github(GITHUB_KEY)

@micropub.route("/micropub", methods=["GET", "POST"])
@requires_indieauth
def micropub_endpoint():
    if request.method == "POST":
        # check content type
        if not request.headers["Content-Type"].startswith("multipart/form-data") and not request.headers["Content-Type"].startswith("application/x-www-form-urlencoded") and not request.headers["Content-Type"].startswith("application/json"):
            return jsonify({"message": "Please send your request with the Content-Type application/x-www-form-urlencoded, application/json or multipart/form-data."}), 400

        if request.headers["Content-Type"].startswith("application/json"):
            object_type = request.json
        elif request.headers["Content-Type"].startswith("multipart/form-data"):
            # get all photos from request.files
            object_type = request.form.to_dict()
            if request.files.getlist("photo[]"):
                photo_list = []
                for photo in request.files.getlist("photo[]"):
                    photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))
                    photo_r = requests.post(MEDIA_ENDPOINT_URL, files={"file": (secure_filename(photo.filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"), 'image/jpeg')})
                    object_type = request.form.to_dict()
                    photo_list += [photo_r.headers.get("Location")]
                object_type["photo"] = photo_list
            else:
                photo = request.files.get("photo")  
                photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))
                photo_r = requests.post(MEDIA_ENDPOINT_URL, files={"file": (secure_filename(request.files.get("photo").filename),open(os.path.join(UPLOAD_FOLDER, secure_filename(request.files.get("photo").filename)), "rb"), 'image/jpeg')})
                object_type["photo"] = photo_r.headers.get("Location")
        else:
            object_type = request.form.to_dict()

        if object_type.get("access_token"):
            del object_type["access_token"]

        if not object_type.get("properties"):
            object_type["properties"] = {}

        if object_type.get("in-reply-to"):
            if type(object_type.get("in-reply-to")) == list:
                object_type["properties"]["in-reply-to"] = object_type.get("in-reply-to")
            else:
                object_type["properties"]["in-reply-to"] = [object_type.get("in-reply-to")]
        elif object_type.get("like-of"):
            if type(object_type.get("like-of")) == list:
                object_type["properties"]["like-of"] = object_type.get("like-of")
            else:
                object_type["properties"]["like-of"] = [object_type.get("like-of")]
        elif object_type.get("repost-of"):
            if type(object_type.get("repost-of")) == list:
                object_type["properties"]["repost-of"] = object_type.get("repost-of")
            else:
                object_type["properties"]["repost-of"] = [object_type.get("repost-of")]
        elif object_type.get("bookmark-of"):
            if type(object_type.get("bookmark-of")) == list:
                object_type["properties"]["bookmark-of"] = object_type.get("bookmark-of")
            else:
                object_type["properties"]["bookmark-of"] = [object_type.get("bookmark-of")]

        if object_type.get("properties") and object_type["properties"].get("content") and type(object_type["properties"].get("content")[0]) == dict:
            content = object_type["properties"].get("content")[0].get("html")
            del object_type["properties"]["content"]
        elif object_type.get("properties") and object_type["properties"].get("content") and type(object_type["properties"].get("content")[0]) == str:
            content = object_type["properties"].get("content")[0]
            del object_type["properties"]["content"]
        elif object_type.get("p-rsvp") and object_type["p-rsvp"]["properties"].get("content") and type(object_type["p-rsvp"]["properties"].get("content")[0]) == str:
            content = object_type["p-rsvp"]["properties"].get("content")[0]
            del object_type["p-rsvp"]["properties"]["content"]
        elif object_type.get("p-rsvp") and object_type["p-rsvp"]["properties"].get("content") and type(object_type["p-rsvp"]["properties"].get("content")[0]) == dict:
            content = object_type["p-rsvp"]["properties"].get("content")[0].get("html")
            del object_type["p-rsvp"]["properties"]["content"]
        elif object_type.get("drank") and object_type["drank"][0]["properties"].get("content") and type(object_type["drank"][0]["properties"].get("content")[0]) == dict:
            content = object_type["drank"][0]["properties"].get("content")[0].get("html")
            del object_type["drank"][0]["properties"]["content"]
        elif object_type.get("drank") and object_type["drank"][0]["properties"].get("content") and type(object_type["drank"][0]["properties"].get("content")[0]) == str:
            content = object_type["drank"][0]["properties"].get("content")[0]
            del object_type["drank"][0]["properties"]["content"]
        elif object_type.get("properties") and object_type.get("properties").get("checkin") and object_type["properties"]["checkin"][0]["properties"].get("content") and type(object_type["properties"]["checkin"][0]["properties"].get("content")[0]) == dict:
            content = object_type["properties"]["checkin"][0]["properties"].get("content")[0].get("html")
            del object_type["properties"]["checkin"][0]["properties"]["content"]
        elif object_type.get("properties") and object_type.get("properties").get("checkin") and object_type["properties"]["checkin"][0]["properties"].get("content") and type(object_type["properties"]["checkin"][0]["properties"].get("content")[0]) == str:
            content = object_type["properties"]["checkin"][0]["properties"].get("content")[0]
            del object_type["properties"]["checkin"][0]["properties"]["content"]
        else:
            content = ""

        content_to_remove = object_type.get("content")

        if content_to_remove:
            del object_type["content"]

        if object_type.get("properties") and object_type.get("properties").get("checkin"):
            front_matter = yaml.dump(object_type["properties"]["checkin"][0]["properties"])
        elif object_type.get("p-rsvp") and object_type.get("p-rsvp").get("properties"):
            front_matter = yaml.dump(object_type.get("p-rsvp").get("properties"))
        elif object_type.get("properties"):
            front_matter = yaml.dump(object_type["properties"])
        elif object_type.get("drank"):
            front_matter = yaml.dump(object_type["drank"][0]["properties"])
        else:
            front_matter = yaml.dump(object_type)

        repo = g.get_repo("capjamesg/jamesg.blog")

        if object_type.get("type"):
            post_type = object_type.get("type")[0].replace("h-", "")
        elif object_type.get("h"):
            post_type = object_type.get("h")
        else:
            post_type = None

        if object_type.get("url"):
            url = object_type.get("url")
        else:
            url = ""

        if object_type.get("action"):
            action = object_type.get("action")
        else:
            action = "create"

        if action == "delete":
            return create_items.delete_post(repo, url)
        elif action == "undelete":
            return create_items.undelete_post(repo, url)
        elif action == "update":
            return create_items.update_post(repo, url, front_matter)

        if object_type.get("p-rsvp"):
            return create_items.process_rsvp(repo, front_matter, content)
        elif object_type.get("in-reply-to"):
            return create_items.process_reply(repo, front_matter, content)
        elif object_type.get("like-of"):
            return create_items.process_like(repo, front_matter)
        elif object_type.get("repost-of"):
            return create_items.process_repost(repo, front_matter)
        elif object_type.get("bookmark-of"):
            return create_items.process_bookmark(repo, front_matter)
        elif object_type.get("properties") and object_type.get("properties").get("checkin"):
            return create_items.process_checkin(repo, front_matter, content)
        if object_type.get("drank"):
            return create_items.process_coffee_post(repo, front_matter, content)
        elif post_type == "entry":
            return create_items.process_post(repo, front_matter, content)
        elif post_type != "entry" and post_type != "in-reply-to":
            return jsonify({"message": "Only h-entry or in-reply-to posts are accepted."}), 400
        else:
            return jsonify({"message": "Invalid post type."}), 400

    if request.args.get("q") and request.args.get("q") == "config":
        # This is deliberately empty to comply with the micropub spec
        response = {"media-endpoint": MEDIA_ENDPOINT_URL, "syndicate-to": []}
        return jsonify(response)
    elif request.args.get("q") and request.args.get("q") == "syndicate-to":
        response = {"syndicate-to": []}
        return jsonify(response)
    elif request.args.get("q") and request.args.get("q") == "source" and request.args.get("url"):
        try:
            folder = request.args.get("url").split("/")[-2]
            url = request.args.get("url").split("/")[-1]

            with open(HOME_FOLDER + "_{}/{}.md".format(folder, url), "r") as file:
                content = file.readlines()

            end_of_yaml = content[1:].index("---\n") + 1

            yaml_to_json = yaml.load("".join([c for c in content[:end_of_yaml] if "---" not in c]), Loader=yaml.SafeLoader)

            yaml_to_json["content"] = content[end_of_yaml + 1:]

            final_properties = {}

            if request.args.getlist("properties[]"):
                for prop in request.args.getlist("properties[]"):
                    final_properties[prop] = yaml_to_json.get(prop)
            else:
                final_properties = yaml_to_json

            response = {"type": ["h-entry"], "properties": final_properties}

            return jsonify(response), 200
        except:
            abort(404)
    else:
        return abort(400)

@micropub.route("/media", methods=["POST"])
def media_endpoint():
    if request.method == "POST":
        if not request.headers["Content-Type"].startswith("multipart/form-data"):
            return jsonify({"message": "Please send your request with the Content-Type multipart/form-data."}), 400

        file = request.files.get("file")
        
        if file == None:
            return jsonify({"message": "Please send a file."}), 400

        # get file extension
        ext = os.path.splitext(file.filename)[1]
        if ext not in (".jpg", ".jpeg", ".png", ".gif"):
            return jsonify({"message": "Please send a valid image file."}), 400

        filename = "".join(random.sample(string.ascii_letters, 5)) + secure_filename(file.filename)
        # save image as file then open with PIL for resizing
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        if ext == ".jpg" or ext == ".jpeg":
            image_file_local = Image.open(os.path.join(UPLOAD_FOLDER, filename))
            image_file_local = ImageOps.exif_transpose(image_file_local)
            image_file_local.thumbnail((1200, 750))
            image_file_local.save(os.path.join(UPLOAD_FOLDER, filename))

        repo = g.get_repo("capjamesg/jamesg.blog")

        with open(os.path.join(UPLOAD_FOLDER, filename), "rb") as image_file:
            repo.create_file("assets/" + filename, "create image for micropub client", image_file.read(), branch="master")

        resp = jsonify({"message": "Created"})
        resp.headers["Location"] = "https://jamesg.blog/assets/{}".format(filename)
        return resp, 201
    else:
        abort(405)