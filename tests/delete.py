from flask import create_app
import pytest

@pytest.fixture
def create_context():
    app = create_app()
    
    with app.test_client() as client:
        yield client

def delete_post(client):
    result = client.post('/micropub', data={
            "action": "delete",
            "url": "https://jamesg.blog/example/4"
        }
    )

    if result.status_code != 200:
        assert False
    else:
        assert True