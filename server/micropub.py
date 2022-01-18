import os
import string
import random

from flask import jsonify, request, g, Blueprint, abort
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
from github import Github
import requests
import yaml

from . import create_items
from interactions import interactions
from auth.auth_helpers import verify_user, validate_scope
from config import GITHUB_KEY, UPLOAD_FOLDER, MEDIA_ENDPOINT_URL, HOME_FOLDER, ALLOWED_EXTENSIONS

micropub = Blueprint("micropub", __name__)

g = Github(GITHUB_KEY)

@micropub.route("/micropub", methods=["GET", "POST"])
def micropub_endpoint():
    if request.method == "POST":
        has_valid_token, scopes = verify_user(request)

        has_valid_token = True

        if has_valid_token is False:
            abort(403)

        scopes = ["create"]

        # the "create" scope is required to use the endpoint
        
        validate_scope("create", scopes)

        # check content type
        if not request.headers["Content-Type"].startswith("multipart/form-data") \
            and not request.headers["Content-Type"].startswith("application/x-www-form-urlencoded") \
            and not request.headers["Content-Type"].startswith("application/json"):

            return jsonify({"message": "Please send your request with the Content-Type application/x-www-form-urlencoded, \
                application/json or multipart/form-data."}), 400
        
        content = ""

        if request.headers["Content-Type"].startswith("application/json"):
            object_type = request.json
        elif request.headers["Content-Type"].startswith("multipart/form-data"):
            # get all photos from request.files
            object_type = request.form.to_dict()
            if request.files.getlist("photo[]"):
                validate_scope("media", scopes)
                photo_list = []
                for photo in request.files.getlist("photo[]"):
                    photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))
                    photo_r = requests.post(
                        MEDIA_ENDPOINT_URL,
                        files={
                            "file": (
                                secure_filename(photo.filename),
                                open(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)), "rb"),
                                'image/jpeg'
                            )
                        }
                    )
                    object_type = request.form.to_dict()
                    photo_list += [photo_r.headers.get("Location")]
                object_type["photo"] = photo_list
            else:
                photo = request.files.get("photo")  
                photo.save(os.path.join(UPLOAD_FOLDER, secure_filename(photo.filename)))
                photo_r = requests.post(MEDIA_ENDPOINT_URL, 
                    files={
                        "file": (
                            secure_filename(request.files.get("photo").filename),
                            open(os.path.join(UPLOAD_FOLDER, secure_filename(request.files.get("photo").filename)), "rb"),
                            'image/jpeg'
                        )
                    }
                )
                object_type["photo"] = photo_r.headers.get("Location")
            content = request.form.get("content")
        else:
            object_type = request.form.to_dict()

        if object_type.get("access_token"):
            del object_type["access_token"]

        if not object_type.get("properties"):
            object_type["properties"] = {}

        normalize_lists = ["in-reply-to", "like-of", "repost-of", "bookmark-of", "syndication"]

        for item in normalize_lists:
            if object_type.get(item) and type(object_type.get(item)) == list:
                object_type["properties"][item] = object_type.get(item)
            elif object_type.get(item) and type(object_type.get(item)) != list:
                object_type["properties"][item] = [object_type.get(item)]
    
        root_properties = ["p-rsvp", "checkin"]

        if object_type.get("properties") and object_type["properties"].get("content") and type(object_type["properties"].get("content")[0]) == dict:
            content = object_type["properties"].get("content")[0].get("html")
            del object_type["properties"]["content"]
        elif object_type.get("properties") and object_type["properties"].get("content") and type(object_type["properties"].get("content")[0]) == str:
            content = object_type["properties"].get("content")[0]
            del object_type["properties"]["content"]

        for root_property in root_properties:
            if object_type.get(root_property) and not object_type.get("drank") \
                and object_type[root_property]["properties"].get("content") \
                and type(object_type[root_property]["properties"].get("content")[0]) == str:

                content = object_type[root_property]["properties"].get("content")[0]
                del object_type[root_property]["properties"]["content"]

        content_to_remove = object_type.get("content")

        if content_to_remove:
            del object_type["content"]

        if object_type.get("properties") and object_type.get("properties").get("checkin"):
            front_matter = yaml.dump(object_type["properties"])
        elif object_type.get("p-rsvp") and object_type.get("p-rsvp").get("properties"):
            front_matter = yaml.dump(object_type.get("p-rsvp").get("properties"))
        elif object_type.get("properties"):
            front_matter = yaml.dump(object_type["properties"])
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

        object_types = (
            ("p-rsvp", "rsvp"),
            ("in-reply-to", "webmention"),
            ("like-of", "like"),
            ("repost-of", "repost"),
            ("bookmark-of", "bookmark"),
            ("watch-of", "watch")
        )

        for item in object_types:
            property_value, interaction_name = item

            if object_type.get(property_value) or object_type["properties"].get(property_value):
                return create_items.process_social(repo, front_matter, interactions.get(interaction_name), content)

        if action == "delete":
            validate_scope("delete", scopes)
            return create_items.delete_post(repo, url)

        if action == "undelete":
            validate_scope("undelete", scopes)
            return create_items.undelete_post(repo, url)

        if action == "update":
            validate_scope("update", scopes)
            return create_items.update_post(repo, url, front_matter, content)

        if object_type.get("properties") and object_type.get("properties").get("checkin"):
            return create_items.process_checkin(repo, front_matter, content)

        if post_type == "entry":
            return create_items.process_social(repo, front_matter, interactions.get("note"), content)
        
        return create_items.process_social(repo, front_matter, interactions.get("note"), content)

    if request.args.get("q") and request.args.get("q") == "config":
        # This is deliberately empty to comply with the micropub spec
        response = {"media-endpoint": MEDIA_ENDPOINT_URL, "syndicate-to": []}
        return jsonify(response)

    if request.args.get("q") and request.args.get("q") == "syndicate-to":
        response = {"syndicate-to": []}
        return jsonify(response)
        
    if request.args.get("q") and request.args.get("q") == "source" and request.args.get("url"):
        try:
            folder = request.args.get("url").split("/")[-2]
            url = request.args.get("url").split("/")[-1]

            with open(HOME_FOLDER + f"_{folder}/{url}.md", "r") as file:
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
    
    return abort(400)

@micropub.route("/media", methods=["POST"])
def media_endpoint():
    has_valid_token, scopes = verify_user(request)

    if has_valid_token is False:
        abort(403)

    # the "media" scope is required to use the endpoint

    validate_scope("media", scopes)

    if request.method == "POST":
        if not request.headers["Content-Type"].startswith("multipart/form-data"):
            return jsonify({"message": "Please send your request with the Content-Type multipart/form-data."}), 400

        file = request.files.get("file")
        
        if file is None:
            return jsonify({"message": "Please send a file."}), 400

        # get file extension
        if "." in file.filename:
            ext = file.filename.split(".")[-1]
        else:
            return jsonify({"message": "Please send a file with an extension."}), 400

        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"message": "Please send a valid image file."}), 400

        filename = "".join(random.sample(string.ascii_letters, 5)) + "-" + "." + ext

        # save image as file then open with PIL for resizing

        file.save(os.path.join(UPLOAD_FOLDER, filename))

        if ext in (".jpg", ".jpeg"):
            image_file_local = Image.open(os.path.join(UPLOAD_FOLDER, filename))
            image_file_local = ImageOps.exif_transpose(image_file_local)
            image_file_local.thumbnail((1200, 750))
            image_file_local.save(os.path.join(UPLOAD_FOLDER, filename))

        repo = g.get_repo("capjamesg/jamesg.blog")

        with open(os.path.join(UPLOAD_FOLDER, filename), "rb") as image_file:
            repo.create_file("assets/" + filename, "create image for micropub client", image_file.read(), branch="main")

        resp = jsonify({"message": "Created"})
        resp.headers["Location"] = f"https://jamesg.blog/assets/{filename}"
        return resp, 201
    else:
        abort(405)