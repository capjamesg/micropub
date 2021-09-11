# Micropub Client and Endpoint

This repository contains the code behind my Micropub client and endpoint. Unusually, the client and endpoint are both part of the same codebase. This is because I built this client and endpoint concurrently and wanted to keep the code as part of the same project.

The client.py file contains all of the code for the Micropub client. micropub_helper.py, create_items.py, and micropub.py contain code relevant to the Micropub server.

This application is powered by Python Flask.

![Micropub homepage](screenshot.png)

## Specification Compliance

This project is in development. As a result, the contents of this repository have not yet passed the Micropub client or server specifciations published on [micropub.rocks](https://micropub.rocks/).

So far, the receiving end has 30 of the 34 specification requirements in the micropub.rocks implementation report. The implementation report is here:

https://micropub.rocks/implementation-reports/servers/593/qcErwj2OOC2MiSqE6QeU

## Configuration

To use this endpoint, you need to create a config.py file with the following values:

    UPLOAD_FOLDER = "/path/to/website/assets/folder/"
    ALLOWED_EXTENSIONS = set(["png", "jpeg", "jpg"])
    HOME_FOLDER = "/path/to/folder/for/website/"
    ENDPOINT_URL = "https://yourmicropubendpoint.com/micropub"
    MEDIA_ENDPOINT_URL = "https://yourmicropubendpoint.com/media"

    GITHUB_KEY = "GITHUB_ACCESS_TOKEN"
    GOOGLE_API_KEY = "GOOGLE_CLOUD_API_KEY"

These values are all required for the endpoint to work. UPLOAD_FOLDER and HOME_FOLDER should be where you keep your website assets folder and website root folder, respectively. In my case, UPLOAD_FOLDER points to my /assets/ folder in my Jekyll repository and HOME_FOLDER points to my root folder in my Jekyll repository.

This project uses PyGitHub to upload posts published through the Micropub server to GitHub. For this feature to work, you need to specify a GitHub access token that has access to read and write to a repository.

The Google API key is used for finding locations when you post a checkin. This feature is only implemented when one does not specify the address of where they are in a checkin. To disable this feature, go to the process_checkin() function in create_items.py and comment out the code related to the Google Cloud API.

## Relevant Resources

Here are some relevant resources that you might find useful if you are interested in building a Micropub client or server or would like to use the one in this repository:

- [Micropub](https://indieweb.org/Micropub)
- [Micropub Specification](https://www.w3.org/TR/micropub/)