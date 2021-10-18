from bs4 import BeautifulSoup
import requests
import mf2py

def get_reply_context(url, request_type):
    h_entry = None
    site_supports_webmention = False

    if request_type == "like-of" or request_type == "repost-of" or request_type == "bookmark-of" or request_type == "in-reply-to" and (url.startswith("https://") or url.startswith("http://")):
        parsed = mf2py.parse(requests.get(url).text)

        supports_webmention = requests.get("https://webmention.jamesg.blog/discover?target={}".format(url))

        if supports_webmention.status_code == 200:
            if supports_webmention.json().get("success") == True:
                site_supports_webmention = True

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        if parsed["items"] and parsed["items"][0]["type"] == ["h-entry"]:
            h_entry = parsed["items"][0]

            if h_entry["properties"].get("author"):
                author_url = h_entry['properties']['author'][0]['properties']['url'][0] if h_entry['properties']['author'][0]['properties'].get('url') else None
                author_name = h_entry['properties']['author'][0]['properties']['name'][0] if h_entry['properties']['author'][0]['properties'].get('name') else None
                author_image = h_entry['properties']['author'][0]['properties']['photo'][0] if h_entry['properties']['author'][0]['properties'].get('photo') else None
                if author_url.startswith("/"):
                    author_url = url.split("/")[0] + "//" + domain + author_url

                if author_image.startswith("/"):
                    author_image = url.split("/")[0] + "//" + domain + author_image
            else:
                author_url = None
                author_name = None
                author_image = None

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
                post_body = None

            # get p-name
            if h_entry["properties"].get("p-name"):
                p_name = h_entry["properties"]["p-name"][0]
            else:
                p_name = None

            if not author_url.startswith("https://") and not author_url.startswith("http://"):
                author_url = "https://" + author_url

            h_entry = {"author_image": author_image, "author_url": author_url, "author_name": author_name, "post_body": post_body, "p-name": p_name}

            return h_entry, site_supports_webmention
            
        h_entry = {}

        try:
            soup = BeautifulSoup(requests.get(url).text, "html.parser")

            page_title = soup.find("title")

            if page_title:
                page_title = page_title.text

            # get body tag
            main_tag = soup.find("body")

            if main_tag:
                p_tag = main_tag.find("p")
                if p_tag:
                    p_tag = p_tag.text
                else:
                    p_tag = None
            else:
                p_tag = None

            if soup.select('.e-content'):
                p_tag = soup.select('.e-content')[0].text
                p_tag = " ".join([w for w in p_tag.split(" ")[:75]])

            if soup.select('.u-photo'):
                photo_url = soup.select('.u-photo')[0]['src']
                
            favicon = soup.find("link", rel="icon")

            if favicon and not photo_url:
                photo_url = favicon["href"]
                if not photo_url.startswith("https://") or not photo_url.startswith("http://"):
                    photo_url = "https://" + domain + photo_url
            else:
                photo_url = None

            if not domain.startswith("https://") and not domain.startswith("http://"):
                author_url = "https://" + domain

            if page_title[:10] == p_tag[:10]:
                page_title = None

            h_entry = {"p-name": page_title, "post_body": p_tag, "author_image": photo_url, "author_url": domain, "author_name": domain}

            return h_entry, site_supports_webmention
        except:
            pass

        try:
            if parsed["items"][0]["properties"].get("photo"):
                photo_url = parsed["items"][0]["properties"]["photo"][0]
                if not photo_url.startswith("https://") or not photo_url.startswith("http://"):
                    photo_url = "https://" + domain + photo_url

            if len(parsed["items"]) > 0:
                if parsed["items"][0]["properties"].get("photo"):
                    author_name = parsed["items"][0]["properties"]["name"][0]
                else:
                    author_name = h_entry["author_name"]

                if parsed["items"][0]["properties"].get("url"):
                    author_url = parsed["items"][0]["properties"]["url"][0]
                else:
                    author_url = h_entry["author_url"]

            h_entry = {"author_image": photo_url, "author_url": author_url, "author_name": author_name, "post_body": p_tag, "p-name": page_title}
            
            return h_entry, site_supports_webmention
        except:
            pass

    return h_entry, site_supports_webmention