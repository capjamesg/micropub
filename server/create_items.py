import os
import string
import random
import datetime

from flask import jsonify
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
import indieweb_utils
from github import Github
import mimetypes
import requests
import yaml

from config import GITHUB_KEY, HOME_FOLDER, GOOGLE_API_KEY, TWITTER_BEARER_TOKEN
from . import micropub_helper

g = Github(GITHUB_KEY)
            
def save_file_from_context(url):
    photo_request = requests.get(url)

    file_name = None

    if photo_request.status_code == 200:
        fifteen_random_letters = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
        
        mime_type = mimetypes.guess_type(url)

        if mime_type[0] is not None:
            ext_text = mimetypes.guess_extension(mime_type[0])

            file_name = fifteen_random_letters + ext_text

            repo = g.get_repo("capjamesg/jamesg.blog")

            with open(HOME_FOLDER + f"{file_name}", "wb") as file:
                file.write(photo_request.content)

            repo.create_file("assets/" + file_name, "create image for micropub client", photo_request.content, branch="main")

    return file_name

def process_social(repo, front_matter, interaction, content=None):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = interaction.get("layout")

    if json_content.get(interaction.get("attribute")):
        target = json_content.get(interaction.get("attribute"))[0]

        print(target)

        if target.get("bookmark-of"):
            target = target.get("bookmark-of")
        elif target.get("like-of"):
            target = target.get("like-of")
        elif target.get("repost-of"):
            target = target.get("repost-of")
        else:
            target = None
    else:
        target = None

    if target and isinstance(target, str) and (target.startswith("https://") or target.startswith("http://")):
        title_req = requests.get(target)

        soup = BeautifulSoup(title_req.text, "lxml")

        if title_req.status_code == 200 and soup and soup.title and soup.title.string:
            title = soup.title.string.strip().replace("\n", "")
        else:
            title = target.replace("https://", "").replace("http://", "")

    if target:
        h_entry, _ = indieweb_utils.get_reply_context(target, twitter_bearer_token=TWITTER_BEARER_TOKEN)

        if h_entry:
            json_content["context"] = h_entry

        # if h_entry.get("author") and h_entry["author"].get("photo"):
        #     file_name = save_file_from_context(h_entry["author"]["photo"])

        #     if file_name != None:
        #         h_entry["author"]["photo"] = f"/assets/{file_name}"

        # if h_entry.get("post_photo_url"):
        #     file_name = save_file_from_context(h_entry["post_photo_url"])

        #     if file_name != None:
        #         h_entry["author"]["photo"] = f"/assets/{file_name}"

        # save target url to wayback machine
        # requests.get("https://web.archive.org/save/" + target)

    if (content is None or content == "") and target:
        content = f"I {interaction.get('keyword')} <a href='{target}' class='u-{interaction.get('attribute')}'>{title}</a>."
        title = f"{interaction.get('keyword').title()} {title}"
    else:
        title = f"{interaction.get('keyword').title()}"

    front_matter = yaml.dump(json_content)

    # random_sequence = "".join(random.sample(string.ascii_letters, 3))

    # with open(HOME_FOLDER + f"random-{random_sequence}.txt", "w+") as f:
    #     f.write(content)
    
    # if "<pre lang='python'>" in content:
    #     with open(HOME_FOLDER + f"random-{random_sequence}.txt", "r") as f:
    #         content = colors.get_rendered_html(f.read(), "python")
    # elif "<pre lang='bash'>" in content:
    #     with open(HOME_FOLDER + f"random-{random_sequence}.txt", "r") as f:
    #         content = colors.get_rendered_html(f.read(), "bash")

    # os.remove(HOME_FOLDER + f"random-{random_sequence}.txt")

    return write_to_file(
        front_matter,
        content,
        repo,
        title,
        interaction.get("folder"),
        category=interaction.get("category")
    ), 201

def process_checkin(repo, front_matter, content):
    json_content = yaml.load(front_matter, Loader=yaml.SafeLoader)

    json_content["layout"] = "social_post"

    source = None

    if json_content.get("syndication") and isinstance(json_content.get("syndication"), list) and \
        json_content.get("syndication")[0].startswith("https://www.swarmapp.com"):
        source = "swarm"

    if source != "swarm":
        if not json_content.get("name")[0] or not json_content.get("latitude") or not json_content.get("longitude"):
            return jsonify({"message": "Please enter a venue name, latitude, and longitude."}), 400

        if not json_content.get("street_address") or not json_content.get("locality") \
            or not json_content.get("region") or not json_content.get("country_name"):

            url_params = f"latlng={json_content.get('latitude')},{json_content.get('longitude')}&key={GOOGLE_API_KEY}"

            url = f"https://maps.googleapis.com/maps/api/geocode/json?{url_params}"
            
            r = requests.get(url)

            if r.status_code == 200:
                data = r.json()

                if len(data["results"]) > 0:
                    results = data["results"][0]

                    if not json_content.get("street_address"):
                        json_content["street_address"] = results["formatted_address"]
                    
                    if not json_content.get("locality"):
                        json_content["locality"] = results["address_components"][2]["long_name"]
                    
                    if not json_content.get("region"):
                        json_content["region"] = results["address_components"][4]["long_name"]

                    if not json_content.get("country_name"):
                        json_content["country_name"] = results["address_components"][-2]["long_name"]

        slug = json_content.get("name")[0] \
            .replace(" ", "-") \
            .replace(".", "-") \
            .replace("-", "") \
            .replace(",", "") \
            .lower() + "-" + "".join(random.sample(string.ascii_letters, 3))

        if not content:
            content = f"Checked in to {json_content.get('name')[0].replace(':', '')}."

        title = f"Checkin to {json_content.get('name')[0]}"
    else:
        slug = "".join(random.sample(string.ascii_letters, 3))

        if not content:
            content = f"Checked in to {json_content['checkin'][0]['properties']['name'][0].replace(':', '')}."
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

    if not json_content.get("category"):
        if category is not None and isinstance(category, list):
            json_content["category"] = category
        elif category is not None and isinstance(category, str):
            json_content["category"] = [category]

    if post_name:
        json_content["title"] = post_name

    if json_content.get("is_hidden"):
        if json_content.get("is_hidden") == "yes":
            json_content["sitemap"] = "false"
        else:
            json_content["sitemap"] = "true"

    if json_content.get("syndication") and "twitter" in json_content["syndication"]:
        twitter_syndication_string = """
        \n <p>This post was syndicated to <a href='https://twitter.com/capjamesg'>Twitter</a>.</p>
        <a href='https://brid.gy/publish/twitter'></a>
        """

        content = content + twitter_syndication_string

    # add brid.gy fed link so posts can be syndicated to the fediverse
    # do this for all posts for now
    # if json_content.get("syndication") and "fediverse" in json_content["syndication"]:
    content = content + "\n<a href='https://fed.brid.gy/'></a>"
    
    json_content["posted_using"] = "my Micropub server"
    json_content["posted_using_url"] = "https://github.com/capjamesg/micropub"

    front_matter = yaml.dump(json_content)
    
    slug = datetime.datetime.now().strftime("%Y-%m-%d") + "-" + str(random.randint(100, 999))

    with open(HOME_FOLDER + f"{folder_name}/{slug}.md", "w+") as file:
        file.write("---\n")
        file.write(front_matter)
        file.write("---\n")
        file.write(content)

    with open(HOME_FOLDER + f"{folder_name}/{slug}.md", "r") as file:
        repo.create_file(
            f"{folder_name}/" + slug + ".md",
            "create post from micropub client",
            file.read(),
            branch="main"
        )

    resp = jsonify({"message": "Created"})
    resp.headers["Location"] = f"https://jamesg.blog/{folder_name.replace('_', '')}/{slug}"

    return resp

def undelete_post(repo, url):
    repo = g.get_repo("capjamesg/jamesg.blog")

    url = url.strip("/").split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == "-"]).lower()
    url = secure_filename(url)

    contents, _, folder = micropub_helper.check_if_exists(url, repo, get_contents=False)
    
    if contents is None and folder is None:
        return jsonify({"message": "The post you tried to undelete does not exist."}), 404
    
    repo.create_file(
        folder + "/" + url + ".md",
        "undelete post from micropub server",
        contents,
        branch="main"
    )

    return jsonify({"message": "Post undeleted."}), 200

def delete_post(repo, url):
    repo = g.get_repo("capjamesg/jamesg.blog")

    if not url:
        return jsonify({"message": "Please provide a url."}), 400

    url = url.strip("/").split("/")[-1]
    url = "".join([char for char in url if char.isalnum() or char == "-"]).lower()
    url = secure_filename(url)

    contents, repo_file_contents, folder = micropub_helper.check_if_exists(url, repo)
    
    if contents is None and repo_file_contents is None and folder is None:
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

    char_comprehension = [char for char in url if char.isalnum() or char == " " or char == "-" or char == "_"]

    url = "".join(char_comprehension).lower()
    url = url.replace(" ", "-")

    contents, repo_file_contents, folder = micropub_helper.check_if_exists(url, repo)
    
    if contents is None and repo_file_contents is None and folder is None:
        return jsonify({"message": "Post not found."}), 404

    with open(HOME_FOLDER + f"{folder}/{url}.md", "r") as file:
        content = file.readlines()

    end_of_yaml = content[1:].index("---\n") + 1

    yaml_string = "".join([c for c in content[:end_of_yaml] if "---" not in c])

    yaml_to_json = yaml.load(yaml_string, Loader=yaml.SafeLoader)

    if yaml.load(front_matter).get("replace"):
        if not isinstance(yaml.load(front_matter).get("replace"), list):
            return jsonify({"message": "This is not a valid update request."}), 400
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["replace"]

        for k in user_front_matter_to_json:
            if k in yaml_to_json.keys():
                yaml_to_json[k] = user_front_matter_to_json[k][0]

    if yaml.load(front_matter, Loader=yaml.SafeLoader).get("add"):
        if not isinstance(yaml.load(front_matter, Loader=yaml.SafeLoader).get("add"), list):
            return jsonify({"message": "This is not a valid add request."}), 400
            
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["add"]

        for k in user_front_matter_to_json:
            if k in yaml_to_json.keys() and k is not None:
                if yaml_to_json[k] is None:
                    yaml_to_json[k] == user_front_matter_to_json[k]
                else:
                    yaml_to_json[k] += user_front_matter_to_json[k]
            else:
                yaml_to_json[k] = user_front_matter_to_json[k]

    if yaml.load(front_matter, Loader=yaml.SafeLoader).get("delete"):
        if not isinstance(yaml.load(front_matter, Loader=yaml.SafeLoader).get("delete"), list):
            return jsonify({"message": "This is not a valid delete request."}), 400
        user_front_matter_to_json = yaml.load(front_matter, Loader=yaml.SafeLoader)["delete"]

        if isinstance(user_front_matter_to_json) == dict:
            for k in user_front_matter_to_json:
                if k in yaml_to_json.keys():
                    for item in user_front_matter_to_json[k]:
                        yaml_to_json[k].remove(item)

        elif isinstance(user_front_matter_to_json) == list:
            for item in user_front_matter_to_json:
                if item in yaml_to_json.keys():
                    yaml_to_json.pop(item)

    with open(HOME_FOLDER + f"{folder}/{url}.md", "w+") as file:
        file.write("---\n")
        file.write(yaml.dump(yaml_to_json))
        file.write("---\n")
        file.write(full_contents_for_writing)

    with open(HOME_FOLDER + f"{folder}/{url}.md", "r") as file:
        repo.update_file(
            f"{folder}/{url}.md",
            "update post via micropub",
            file.read(),
            repo_file_contents.sha,
            branch="main"
        )

    resp = jsonify({"message": "Post updated."})
    resp.headers["Location"] = original_url

    return resp, 201
