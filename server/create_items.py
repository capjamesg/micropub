from config import *
from flask import jsonify
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from . import micropub_helper
from github import Github
from . import colors
import datetime
import requests
import context
import string
import random
import yaml
import os

g = Github(GITHUB_KEY)

def process_social(repo, front_matter, interaction, content=None):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = interaction.get("layout")

    target = json_content.get(interaction.get("attribute"))

    if not target and interaction.get("attribute") != "coffee" and interaction.get("attribute") != "rsvp" and interaction.get("attribute") != "note":
        return jsonify({"message": "Please enter a {} target.".format(interaction.get("attribute"))}), 400
    elif target:
        target = target[0]

        title_req = requests.get(target)

        soup = BeautifulSoup(title_req.text, "lxml")

        if title_req.status_code == 200 and soup and soup.title and soup.title.string:
            title = soup.title.string.strip().replace("\n", "")
        else:
            title = target.replace("https://", "").replace("http://", "")

    if target:
        h_entry, _ = context.get_reply_context(target, interaction.get("attribute"))

        if h_entry:
            json_content["context"] = h_entry

    if content == None and target:
        content = "I {} <a href='{}' class='u-{}'>{}</a>.".format(interaction.get("keyword"), target, interaction.get("attribute"), title)
        title = "{} {}".format(interaction.get("keyword").title(), title)
    else:
        title = "{}".format(interaction.get("keyword").title())

    front_matter = yaml.dump(json_content)

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

    return write_to_file(front_matter, content, repo, title, interaction.get("folder"), category=interaction.get("category")), 201

def process_checkin(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "social_post"

    source = None

    if json_content.get("syndication") and type(json_content.get("syndication")) == list and \
        json_content.get("syndication")[0].startswith("https://www.swarmapp.com"):
        source = "swarm"

    if source != "swarm":

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

        if not content:
            content = "Checked in to {}.".format(json_content.get("name")[0].replace(":", ""))

        title = "Checkin to {}".format(json_content.get("name")[0])
    else:
        slug = "".join(random.sample(string.ascii_letters, 3))

        if not content:
            content = "Checked in to {}.".format(json_content["checkin"][0]["properties"]["name"][0].replace(":", ""))
            title = content

    if json_content.get("url"):
        json_content["syndicate"] = json_content["url"]
        del json_content["url"]

    front_matter = yaml.dump(json_content)

    return write_to_file(front_matter, content, repo, title, "_checkin", slug=slug, category="Checkin"), 201

def write_to_file(front_matter, content, repo, post_name, folder_name, slug=None, category=None):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    if not json_content.get("layout"):
        json_content["layout"] = "social_post"

    json_content["published"] = datetime.datetime.now()

    if category != None and type(category) == list:
        json_content["category"] = category
    elif category != None and type(category) == str:
        json_content["category"] = [category]

    if post_name:
        json_content["title"] = post_name

    if json_content.get("is_hidden"):
        if json_content.get("is_hidden") == "yes":
            json_content["sitemap"] = "false"
        else:
            json_content["sitemap"] = "true"

    if json_content.get("syndication") and json_content["syndication"][0] == "twitter":
        del json_content["syndication"]

        content = content + "\n <p>This post was syndicated to <a href='https://twitter.com/capjamesg'>Twitter</a>.</p> <a href='https://brid.gy/publish/twitter'></a>"\
        
    json_content["posted_using"] = "my Micropub server"
    json_content["posted_using_url"] = "https://github.com/capjamesg/micropub"

    front_matter = yaml.dump(json_content)
    
    slug = datetime.datetime.now().strftime("%Y-%m-%d") + "-" + str(random.randint(100, 999))

    with open(HOME_FOLDER + "{}/{}.md".format(folder_name, slug), "w+") as file:
        file.write("---\n")
        file.write(front_matter)
        file.write("---\n")
        file.write(content)

    with open(HOME_FOLDER + "{}/{}.md".format(folder_name, slug), "r") as file:
        repo.create_file("{}/".format(folder_name) + slug + ".md", "create post from micropub client", file.read(), branch="main")

    resp = jsonify({"message": "Created"})
    resp.headers["Location"] = "https://jamesg.blog/{}/{}".format(folder_name.replace("_", ""), slug)

    return resp

def undelete_post(repo, url):
    repo = g.get_repo("capjamesg/jamesg.blog")

    url = url.strip("/").split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == "-"]).lower()
    url = secure_filename(url)

    contents, _, folder = micropub_helper.check_if_exists(url, repo, get_contents=False)
    
    if contents == None and folder == None:
        return jsonify({"message": "The post you tried to undelete does not exist."}), 404

    repo.create_file(folder + "/" + url + ".md", "undelete post from micropub server", contents, branch="main")

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
    
    repo.delete_file(contents.path, "remove post via micropub", contents.sha, branch="main")

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
        repo.update_file("{}/{}.md".format(folder, url), "update post via micropub", file.read(), repo_file_contents.sha, branch="main")

    resp = jsonify({"message": "Post updated."})
    resp.headers["Location"] = original_url

    return resp, 201