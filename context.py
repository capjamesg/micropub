from bs4 import BeautifulSoup
from config import TWITTER_BEARER_TOKEN
import requests
import mf2py

def canonicalize_url(url, domain, full_url=None):
    if url.startswith("http://") or url.startswith("https://"):
        return url
    elif url.startswith("//"):
        return "https:" + domain.strip() + "/" + url
    elif url.startswith("/"):
        return "https://" + domain.strip() + "/" + url
    elif url.startswith("./"):
        return full_url + url.replace(".", "")
    elif url.startswith("../"):
        return "https://" + domain.strip() + "/" + url[3:]
    else:
        return "https://" + url

def get_reply_context(url):
    h_entry = None
    photo_url = None
    site_supports_webmention = False

    html_accept_header = {
        'Accept': 'text/html',
        'User-Agent': 'Microsub Client and Server'
    }

    if url.startswith("https://") or url.startswith("http://"):
        req = requests.get(url, timeout=10, verify=False, headers=html_accept_header)

        parsed = mf2py.parse(req.text)

        supports_webmention = requests.get(f"https://webmention.jamesg.blog/discover?target={url}")

        if supports_webmention.status_code == 200:
            if supports_webmention.json().get("success") == True:
                site_supports_webmention = True

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        if parsed["items"] and parsed["items"][0]["type"] == ["h-entry"]:
            h_entry = parsed["items"][0]

            author_url = None
            author_name = None
            author_image = None

            if h_entry["properties"].get("author"):
                if type(h_entry["properties"]["author"][0]) == dict and h_entry["properties"]["author"][0].get("type") == ["h-card"]:
                    author_url = h_entry['properties']['author'][0]['properties']['url'][0] if h_entry['properties']['author'][0]['properties'].get('url') else url
                    author_name = h_entry['properties']['author'][0]['properties']['name'][0] if h_entry['properties']['author'][0]['properties'].get('name') else None
                    author_image = h_entry['properties']['author'][0]['properties']['photo'][0] if h_entry['properties']['author'][0]['properties'].get('photo') else None
                elif type(h_entry["properties"]["author"][0]) == str:
                    if h_entry["properties"].get("author") and h_entry["properties"]["author"][0].startswith("/"):
                        author_url = url.split("/")[0] + "//" + domain + h_entry["properties"].get("author")[0]

                    author = mf2py.parse(requests.get(author_url, timeout=10, verify=False, headers=html_accept_header).text)
                    
                    if author["items"] and author["items"][0]["type"] == ["h-card"]:
                        author_url = h_entry['properties']['author'][0]
                        author_name = author['items'][0]['properties']['name'][0] if author['items'][0]['properties'].get('name') else None
                        author_image = author['items'][0]['properties']['photo'][0] if author['items'][0]['properties'].get('photo') else None

                if author_url != None and author_url.startswith("/"):
                    author_url = url.split("/")[0] + "//" + domain + author_url

                if author_image != None and author_image.startswith("/"):
                    author_image = url.split("/")[0] + "//" + domain + author_image

            if h_entry["properties"].get("content") and h_entry["properties"].get("content")[0].get("html"):
                post_body = h_entry["properties"]["content"][0]["html"]
                soup = BeautifulSoup(post_body, "html.parser")
                post_body = soup.text
                
                favicon = soup.find("link", rel="icon")

                if favicon and not author_image:
                    photo_url = favicon["href"]
                    if not photo_url.startswith("https://") or not photo_url.startswith("http://"):
                        author_image = "https://" + domain + photo_url
                else:
                    author_image = None
            elif h_entry["properties"].get("content"):
                post_body = h_entry["properties"]["content"]
            else:
                soup = BeautifulSoup(req.text, "html.parser")

                p_name = soup.find("title")

                if p_name:
                    p_name = p_name.text

                # delete <header> tags
                for header in soup.find_all("header"):
                    header.decompose()

                if soup.find("article"):
                    post_body = soup.find("article").text
                elif soup.find("main"):
                    post_body = soup.find("main").text
                else:
                    post_body = soup.text

            if post_body:
                post_body = " ".join(post_body.split(" ")[:75]) + " ..."

            # get p-name
            if h_entry["properties"].get("name"):
                p_name = h_entry["properties"]["name"][0]

            if author_url != None and (not author_url.startswith("https://") and not author_url.startswith("http://")):
                author_url = "https://" + author_url

            if not author_name and author_url:
                author_name = author_url.split("/")[2]

            post_photo_url = None
            post_video_url = None

            if h_entry["properties"].get("photo"):
                post_photo_url = canonicalize_url(h_entry["properties"]["photo"][0], domain, url)

            if h_entry["properties"].get("video"):
                post_video_url = canonicalize_url(h_entry["properties"]["video"][0], domain, url)

            # look for featured image to display in reply context
            if post_photo_url == None:
                soup = BeautifulSoup(req.text, "html.parser")

                if soup.find("meta", property="og:image") and soup.find("meta", property="og:image")["content"]:
                    post_photo_url = soup.find("meta", property="og:image")["content"]
                elif soup.find("meta", property="twitter:image") and soup.find("meta", property="twitter:image")["content"]:
                    post_photo_url = soup.find("meta", property="twitter:image")["content"]

            h_entry = {"author_image": author_image, "author_url": author_url, "author_name": author_name, "post_body": post_body, "p-name": p_name}

            if post_photo_url:
                h_entry["post_photo_url"] = post_photo_url

            if post_video_url:
                h_entry["post_video_url"] = post_video_url

            return h_entry, site_supports_webmention

        elif parsed["items"] and parsed["items"][0]["type"] == ["h-card"]:
            h_card = parsed["items"][0]

            if h_card["properties"].get("name"):
                author_name = h_card['properties']['name'][0]
            else:
                author_name = None

            if h_card["properties"].get("photo"):
                author_image = h_card['properties']['photo'][0]
                if author_image.startswith("//"):
                    author_image = "https:" + author_image
                elif author_image.startswith("/"):
                    author_image = url.split("/")[0] + "//" + domain + author_image
                elif author_image.startswith("http://") or author_image.startswith("https://"):
                    author_image = author_image
                else:
                    author_image = "https://" + domain + "/" + author_image
            else:
                author_image = None

            if h_card["properties"].get("note"):
                post_body = h_card['properties']['note'][0]

                post_body = " ".join(post_body.split(" ")[:75]) + " ..."
            else:
                post_body = None

            h_card = {"author_image": author_image, "author_url": url, "author_name": author_name, "post_body": post_body, "p-name": None}

            return h_card, site_supports_webmention
            
        h_entry = {}

        if url.startswith("https://twitter.com"):
            site_supports_webmention = False
            tweet_uid = url.strip("/").split("/")[-1]
            headers = {
                "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"
            }
            r = requests.get(f"https://api.twitter.com/2/tweets/{tweet_uid}?tweet.fields=author_id", headers=headers, timeout=10, verify=False)

            if r and r.status_code != 200:
                return {}, None

            get_author = requests.get(
                f"https://api.twitter.com/2/users/{r.json()['data'].get('author_id')}?user.fields=url,name,profile_image_url,username",
                headers=headers,
                timeout=10,
                verify=False
            )

            if get_author and get_author.status_code == 200:
                photo_url = get_author.json()["data"].get("profile_image_url")
                author_name = get_author.json()["data"].get("name")
                author_url = "https://twitter.com/" + get_author.json()["data"].get("username")
            else:
                photo_url = None
                author_name = None
                author_url = None

            post_body = r.json()["data"].get("text")

            if post_body:
                post_body = " ".join(post_body.split(" ")[:75]) + " ..."

            h_entry = {"p-name": "", "post_body": post_body, "author_image": photo_url, "author_url": author_url, "author_name": author_name}

            return h_entry, site_supports_webmention

        soup = BeautifulSoup(requests.get(url, headers=html_accept_header).text, "lxml")

        page_title = soup.find("title")

        if page_title:
            page_title = page_title.text

        # get body tag
        main_tag = soup.find("body")

        if main_tag:
            p_tag = main_tag.find("h1")
            
            if p_tag:
                p_tag = p_tag.text
            else:
                p_tag = None
        else:
            p_tag = None

        if soup.select('.e-content'):
            p_tag = soup.select('.e-content')[0]

            # get first paragraph
            if p_tag:
                p_tag = p_tag.find_all("p")

                if p_tag:
                    p_tag = " ".join([p.text for p in p_tag[:3]])

                p_tag = " ".join([w for w in p_tag.split(" ")[:75]]) + " ..."
            else:
                p_tag = ""

        post_photo_url = None

        # look for featured image to display in reply context
        if soup.select('.u-photo'):
            post_photo_url = soup.select('.u-photo')[0]['src']
        elif soup.find("meta", property="og:image") and soup.find("meta", property="og:image")["content"]:
            post_photo_url = soup.find("meta", property="og:image")["content"]
        elif soup.find("meta", property="twitter:image") and soup.find("meta", property="twitter:image")["content"]:
            post_photo_url = soup.find("meta", property="twitter:image")["content"]
            
        favicon = soup.find("link", rel="icon")

        if favicon and not photo_url:
            photo_url = favicon["href"]
            if not photo_url.startswith("https://") and not photo_url.startswith("http://"):
                photo_url = "https://" + domain + "/" + photo_url

            r = requests.get(photo_url, headers=html_accept_header, timeout=10, verify=False)

            if r.status_code != 200:
                photo_url = None
        else:
            photo_url = None

        if not domain.startswith("https://") and not domain.startswith("http://"):
            author_url = "https://" + domain

        h_entry = {"p-name": page_title, "post_body": p_tag, "author_image": photo_url, "author_url": "https://" + domain, "author_name": domain}

        if post_photo_url:
            h_entry["post_photo_url"] = post_photo_url

        return h_entry, site_supports_webmention

    return h_entry, site_supports_webmention