import mimetypes
import random
import string

import requests

from config import HOME_FOLDER

h_entry = {"author": {"photo": "https://jamesg.blog/assets/latte_1.jpeg"}}

photo_request = requests.get(h_entry["author"]["photo"])

if photo_request.status_code == 200:
    fifteen_random_letters = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(15)
    )

    mime_type = mimetypes.guess_type(h_entry["author"]["photo"])

    if mime_type:
        ext_text = mimetypes.guess_extension(mime_type[0])

        file_name = fifteen_random_letters + ext_text

        repo = g.get_repo("capjamesg/jamesg.blog")

        with open(HOME_FOLDER + f"{file_name}", "wb") as file:
            file.write(photo_request.content)

        repo.create_file(
            "assets/" + file_name,
            "create image for micropub client",
            photo_request.content,
            branch="main",
        )
