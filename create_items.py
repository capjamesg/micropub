from .config import *
from flask import jsonify
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from . import micropub_helper
from github import Github
from . import colors
import datetime
import requests
import string
import random
import yaml
import os

g = Github(GITHUB_KEY)

def process_like(repo, front_matter):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "like"

    target = json_content.get("like-of")[0]

    if not target:
        return jsonify({"message": "Please enter a like-of target."}), 400

    title_req = requests.get(target)

    soup = BeautifulSoup(title_req.text, "lxml")

    if title_req.status_code == 200 and soup and soup.title and soup.title.string:
        title = soup.title.string
    else:
        title = target.replace("https://", "").replace("http://", "")

    content = "I liked <a href='{}' class='u-like-of'>{}</a> by <a href='{}'>{}</a>.".format(target, title, target.split("://")[1].split("/")[0], target.split("://")[1].split("/")[0])

    front_matter = yaml.dump(json_content)

    return write_to_file(front_matter, content, repo, "Liked {}".format(title), "_likes"), 201

def process_checkin(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "checkin"

    if not json_content.get("name")[0] or not json_content.get("latitude") or not json_content.get("longitude"):
        return jsonify({"message": "Please enter a venue name, latitude, and longitude."}), 400

    if not json_content.get("street_address") or not json_content.get("locality") or not json_content.get("region") or not json_content.get("country_name"):
        r = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng={},{}&key={}".format(json_content.get("latitude"), json_content.get("longitude"), GOOGLE_API_KEY))

        if r.status_code == 200:
            data = r.json()

            if len(data["results"]) > 0:
                if not json_content.get("street_address"):
                    json_content["street_address"] = data["results"][0]["formatted_address"]
                
                if not json_content.get("locality"):
                    json_content["locality"] = data["results"][0]["address_components"][2]["long_name"]
                
                if not json_content.get("region"):
                    json_content["region"] = data["results"][0]["address_components"][4]["long_name"]

                if not json_content.get("country_name"):
                    json_content["country_name"] = data["results"][0]["address_components"][-2]["long_name"]

    slug = json_content.get("name")[0].replace(" ", "-").replace(".", "-").replace("-", "").replace(",", "").lower() + "-" + "".join(random.sample(string.ascii_letters, 3))

    if json_content.get("url"):
        json_content["syndicate"] = json_content["url"]
        del json_content["url"]

    front_matter = yaml.dump(json_content)

    if not content:
        content = "Checked in to {}.".format(json_content.get("name")[0].replace(":", ""))

    return write_to_file(front_matter, content, repo, "Checkin to {}".format(json_content.get("name")[0]), "_checkin", slug=slug), 201

def process_bookmark(repo, front_matter):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "bookmark"

    target = json_content.get("bookmark-of")[0]

    if not target:
        return jsonify({"message": "Please enter a bookmark-of target."}), 400

    title_req = requests.get(target)

    soup = BeautifulSoup(title_req.text, "html.parser")

    if title_req.status_code == 200 and soup and soup.title and soup.title.string:
        title = soup.title.string
    else:
        title = target.replace("https://", "").replace("http://", "")

    content = "I have bookmarked <a href='{}' class='u-bookmark-of h-cite'>{}</a> by <a href='{}'>{}</a> for later reference.".format(target, title, target.split("://")[1].split("/")[0], target.split("://")[1].split("/")[0])

    front_matter = yaml.dump(json_content)

    return write_to_file(front_matter, content, repo, "Bookmarked {}".format(title), "_bookmark"), 201

def process_repost(repo, front_matter):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "repost"

    target = json_content.get("repost-of")[0]

    if not target:
        return jsonify({"message": "Please enter a repost-of target."}), 400

    title_req = requests.get(target)

    soup = BeautifulSoup(title_req.text, "html.parser")

    if title_req.status_code == 200 and soup and soup.title and soup.title.string:
        title = soup.title.string
    else:
        title = target.replace("https://", "").replace("http://", "")

    content = "I enjoyed <a href='{}' class='u-repost-of h-cite'>{}</a> by <a href='{}'>{}</a>.".format(target, title, target.split("://")[1].split("/")[0], target.split("://")[1].split("/")[0])

    front_matter = yaml.dump(json_content)

    return write_to_file(front_matter, content, repo, "Shared {}".format(title), "_repost"), 201

def process_rsvp(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "rsvp"

    if not content or not json_content.get("event_name") or not json_content.get("state"):
        return jsonify({"message": "Please enter an event name, an RSVP state, and a post body."}), 400

    front_matter = yaml.dump(json_content)

    title = "".join([c for c in json_content.get("event_name") if c.isalpha() or c.isdigit() or c == " " or c == "-" or c == "_"])

    return write_to_file(front_matter, content, repo, "RSVP to {}".format(title), "_rsvp"), 201

def process_reply(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "webmention"

    front_matter = yaml.dump(json_content)

    if not content or not json_content.get("in-reply-to"):
        return jsonify({"message": "Please enter post content and an in-reply-to target."}), 400

    title_req = requests.get(json_content.get("in-reply-to")[0])

    soup = BeautifulSoup(title_req.text, "lxml")

    if title_req.status_code == 200 and soup and soup.title and soup.title.string:
        title = soup.title.string
    else:
        title = json_content.get("in-reply-to")[0].replace("https://", "").replace("http://", "")

    return write_to_file(front_matter, content, repo, "Webmention to {}".format(title), "_webmentions"), 201

def process_post(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    categories = json_content.get("categories")
    post_name = json_content.get("title")

    json_content["layout"] = "note"

    if categories == None or len(categories) == 0:
        categories = ["Note"]

    front_matter = yaml.dump(json_content)

    if not content:
        return jsonify({"message": "Please specify a post type and content body."}), 400

    random_sequence = "".join(random.sample(string.ascii_letters, 3))

    with open(HOME_FOLDER + "random-{}.txt".format(random_sequence), "w+") as f:
        f.write(content)
    
    if "<pre lang='python'>" in content:
        with open(HOME_FOLDER + "random-{}.txt".format(random_sequence), "r") as f:
            content = colors.get_rendered_html(f.read(), "python")
    elif "<pre lang='bash'>" in content:
        with open(HOME_FOLDER + "random-{}.txt".format(random_sequence), "r") as f:
            content = colors.get_rendered_html(f.read(), "bash")

    os.remove(HOME_FOLDER + "random-{}.txt".format(random_sequence))

    return write_to_file(front_matter, content, repo, post_name, "_notes"), 201

def write_to_file(front_matter, content, repo, post_name, folder_name, slug=None):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    if post_name != None:
        json_content["title"] = post_name
    else:
        json_content["title"] = " ".join(content.split(" ")[:8]) + " ..."

    json_content["published"] = datetime.datetime.now()

    if json_content.get("is_hidden"):
        if json_content.get("is_hidden") == "yes":
            json_content["sitemap"] = "false"
        else:
            json_content["sitemap"] = "true"

    front_matter = yaml.dump(json_content)
    
    slug = datetime.datetime.now().strftime("%Y-%m-%d") + "-" + str(random.randint(100, 999))

    with open(HOME_FOLDER + "{}/{}.md".format(folder_name, slug), "w+") as file:
        file.write("---\n")
        file.write(front_matter)
        file.write("---\n")
        file.write(content)

    with open(HOME_FOLDER + "{}/{}.md".format(folder_name, slug), "r") as file:
        repo.create_file("{}/".format(folder_name) + slug + ".md", "create post from micropub client", file.read(), branch="master")

    resp = jsonify({"message": "Created"})
    resp.headers["Location"] = "https://jamesg.blog/{}/{}".format(folder_name.replace("_", ""), slug)

    return resp

def process_coffee_post(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    categories = json_content.get("categories")
    post_name = json_content.get("title")

    json_content["layout"] = "drinking"

    if categories == None or len(categories) == 0:
        categories = ["Note"]

    if post_name != None:
        json_content["title"] = "".join([char for char in post_name[0] if char.isalnum() or char == " "])
    else:
        json_content["title"] = content.split(" ")[:3][0]

    if not content:
        return jsonify({"message": "Please specify a post type and content body."}), 400

    front_matter = yaml.dump(json_content)

    return write_to_file(front_matter, content, repo, post_name, "_coffee"), 201

def undelete_post(repo, url):
    repo = g.get_repo("capjamesg/jamesg.blog")

    url = url.strip("/").split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == "-"]).lower()
    url = secure_filename(url)

    contents, _, folder = micropub_helper.check_if_exists(url, repo, get_contents=False)
    
    if contents == None and folder == None:
        return jsonify({"message": "The post you tried to undelete does not exist."}), 404

    repo.create_file(folder + "/" + url + ".md", "undelete post from micropub server", contents, branch="master")

    return jsonify({"message": "Post undeleted."}), 200

def delete_post(repo, url):
    repo = g.get_repo("capjamesg/jamesg.blog")

    if not url:
        return jsonify({"message": "Please provide a url."}), 400

    url = url.strip("/").split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == "-"]).lower()
    url = secure_filename(url)

    contents, repo_file_contents, folder = micropub_helper.check_if_exists(url, repo)
    
    if contents == None and repo_file_contents == None and folder == None:
        return jsonify({"message": "The post you tried to undelete does not exist."}), 404

    contents = repo.get_contents(folder + "/" + url + ".md")
    repo.delete_file(contents.path, "remove post via micropub", contents.sha, branch="master")
    return jsonify({"message": "Post deleted."}), 200

def update_post(repo, url, front_matter, full_contents_for_writing):
    repo = g.get_repo("capjamesg/jamesg.blog")

    original_url = url

    if not url:
        return jsonify({"message": "Please provide a url."}), 400

    url = url.split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == " " or char == "-" or char == "_"]).lower()
    url = url.replace(" ", "-")

    contents, repo_file_contents, folder = micropub_helper.check_if_exists(url, repo)
    
    if contents == None and repo_file_contents == None and folder == None:
        return jsonify({"message": "Post not found."}), 404

    with open(HOME_FOLDER + "{}/{}.md".format(folder, url), "r") as file:
        content = file.readlines()

    end_of_yaml = content[1:].index("---\n") + 1

    yaml_to_json = yaml.load("".join([c for c in content[:end_of_yaml] if "---" not in c]), Loader=yaml.SafeLoader)

    if yaml.load(front_matter).get("replace"):
        if type(yaml.load(front_matter).get("replace")) != list:
            return jsonify({"message": "This is not a valid update request."}), 400
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["replace"]

        for k, v in user_front_matter_to_json.items():
            if k in yaml_to_json.keys():
                yaml_to_json[k] = user_front_matter_to_json[k][0]

    elif yaml.load(front_matter, Loader=yaml.SafeLoader).get("add"):
        if type(yaml.load(front_matter, Loader=yaml.SafeLoader).get("add")) != list:
            return jsonify({"message": "This is not a valid add request."}), 400
            
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["add"]

        for k, v in user_front_matter_to_json.items():
            if k in yaml_to_json.keys() and k != None:
                if yaml_to_json[k] == None:
                    yaml_to_json[k] == user_front_matter_to_json[k]
                else:
                    yaml_to_json[k] += user_front_matter_to_json[k]
            else:
                yaml_to_json[k] = user_front_matter_to_json[k]

    elif yaml.load(front_matter, Loader=yaml.SafeLoader).get("delete"):
        if type(yaml.load(front_matter, Loader=yaml.SafeLoader).get("delete")) != list:
            return jsonify({"message": "This is not a valid delete request."}), 400
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["delete"]

        if type(user_front_matter_to_json) == dict:
            for k, v in user_front_matter_to_json.items():
                if k in yaml_to_json.keys():
                    for item in user_front_matter_to_json[k]:
                        yaml_to_json[k].remove(item)
        elif type(user_front_matter_to_json) == list:
            for item in user_front_matter_to_json:
                if item in yaml_to_json.keys():
                    yaml_to_json.pop(item)

    with open(HOME_FOLDER + "{}/{}.md".format(folder, url), "w+") as file:
        file.write("---\n")
        file.write(yaml.dump(yaml_to_json))
        file.write("---\n")
        file.write(full_contents_for_writing)

    with open(HOME_FOLDER + "{}/{}.md".format(folder, url), "r") as file:
        print(file.read())
    #     repo.update_file("{}/{}.md".format(folder, url), "update post via micropub", file.read(), repo_file_contents.sha, branch="master")

    resp = jsonify({"message": "Post updated."})
    resp.headers["Location"] = original_url

    return resp, 201