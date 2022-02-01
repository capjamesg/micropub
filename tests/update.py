import pytest
from flask import create_app


@pytest.fixture
def create_context():
    app = create_app()

    with app.test_client() as client:
        yield client


def update_note(client):
    result = client.post(
        "/micropub",
        data={
            "action": "update",
            "url": "https://jamesg.blog/example/1",
            "replace": {"content": [{"html": "This is an updated note."}]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def update_coffee_post(client):
    result = client.post(
        "/micropub",
        data={
            "action": "update",
            "url": "https://jamesg.blog/example/2",
            "replace": {"roaster": ["Test Roaster"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True


def update_rsvp(client):
    result = client.post(
        "/micropub",
        data={
            "action": "update",
            "url": "https://jamesg.blog/example/3",
            "replace": {"rsvp": ["no"]},
        },
    )

    if result.status_code != 200:
        assert False
    else:
        assert True
