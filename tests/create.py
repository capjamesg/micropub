import pytest
from flask import create_app


@pytest.fixture
def create_context():
    app = create_app()

    with app.test_client() as client:
        yield client


def create_reply(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "in-reply-to": ["https://example.com/post/1"],
            "properties": {
                "content": [{"html": "This is a reply."}],
                "category": ["Category"],
            },
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_like(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "like-of": ["https://example.com/post/1"],
            "properties": {"category": ["Like"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_repost(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "repost-of": ["https://example.com/post/1"],
            "properties": {"category": ["Repost"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_bookmark(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "bookmark-of": ["https://example.com/post/1"],
            "properties": {"category": ["Bookmark"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_rsvp(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "rsvp": ["yes"],
            "properties": {"category": ["RSVP"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_note(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "properties": {
                "content": [{"html": "This is a note."}],
                "category": ["Category"],
            },
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def create_coffee_post(client):
    result = client.post(
        "/micropub",
        data={
            "type": ["h-entry"],
            "properties": {
                "content": [{"html": "This is a coffee post."}],
                "category": ["Coffee"],
                "varietals": ["Test Varietals"],
            },
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def query_discovery_endpoint(client):
    result = client.get("/micropub?q=config")

    if result.status_code != 200:
        assert False
    else:
        assert True
