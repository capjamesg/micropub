import config
import os

def check_folder(folder_name, url, get_contents, repo):
    if os.path.exists(HOME_FOLDER + "{}/{}.md".format(folder_name, url)):
        with open(HOME_FOLDER + "{}/{}.md".format(folder_name, url), "r") as file:
            if get_contents == True:
                contents = file.readlines()
            else:
                contents = file.read()

        if get_contents == True:
            repo_file_contents = repo.get_contents("{}/{}.md".format(folder_name, url), ref="master")
        else:
            repo_file_contents = None

        return contents, repo_file_contents, folder_name
    else:
        return None, None, None

def check_if_exists(url, repo, get_contents=True):
    contents = None
    repo_file_contents = None
    folder = None

    folder_names = ["_coffee", "_webmentions", "_notes", "_likes", "_bookmark", "_rsvp", "_checkin"]

    for name in folder_names:
        contents, repo_file_contents, folder = check_folder(name, url, get_contents, repo)

        if contents:
            return contents, repo_file_contents, folder
    
    return contents, repo_file_contents, folder