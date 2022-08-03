from readline import redisplay
import pytest

from model.conn import create_engine_session, Base
from main import app, get_db

from fastapi.testclient import TestClient
import requests
import bcrypt


engine, session = create_engine_session(test=True)


def setup_function():
    Base.metadata.create_all(bind=engine)
    hashed_pw = bcrypt.hashpw(b'testpassword', bcrypt.gensalt()).decode('utf-8')
    
    engine.execute(f"INSERT INTO users (id, name, email, profile, hashed_password) \
        VALUES (1, 'test_client1', 'test_client1@test.com', 'Test profile', '{hashed_pw}');")
    engine.execute(f"INSERT INTO users (id, name, email, profile, hashed_password) \
        VALUES (2, 'test_client2', 'test_client2@test.com', 'Test profile', '{hashed_pw}');")
    
    engine.execute("INSERT INTO tweets (user_id, tweet) VALUES (1, 'HELLO WORLD!');")
    
    
def teardown_function():
    engine.execute('TRUNCATE TABLE users;')
    engine.execute('TRUNCATE TABLE tweets;')
    engine.execute('TRUNCATE TABLE users_follow_list;')
    

def override_get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def api():
    app.dependency_overrides[get_db] = override_get_db
    test_app = TestClient(app)
    return test_app


def test_ping(api):
    response = api.get('/ping')
    assert response.status_code == 200


def test_sign_up(api):
    first_user = {
        'name': 'test_client3',
        'email': 'test_client3@test.com',
        'password': 'testpassword',
        'profile': 'This is Test!'
    }
    response = api.put('/sign-up', json=first_user)
    assert response.status_code == 200, response.text

    integrity_error_case = {
        'name': 'test_client_none',
        'email': 'test_client1@test.com',
        'password': 'testpassword',
        'profile': 'This is Test!'
    }
    response = api.put('/sign-up', json=integrity_error_case)
    assert response.status_code == 400, response.text


def test_login(api):
    data = {
        'email': 'test_client1@test.com',
        'password': 'testpassword'
    }
    response = api.post('/login', json=data)
    assert response.status_code == 200, response.text

    no_user_case = {
        'email': 'no_user@test.com',
        'password': 'nouser'
    }
    response = api.post('/login', json=no_user_case)
    assert response.status_code == 400, response.text

    wrong_case = {
        'email': 'test_client@test.com',
        'password': 'q0101010'
    }
    response = api.post('/login', json=wrong_case)
    assert response.status_code == 400, response.text


def test_follow(api):
    data = {
        'email': 'test_client1@test.com',
        'password': 'testpassword'
    }
    response = api.post('/login', json=data)
    
    token = response.json()['access_token']
    
    data = {'user_id_to_follow': 2}
    response = api.put('/follow',
                       headers={'Authorization': token},
                       json=data)
    assert response.status_code == 200, response.text


def test_unfollow(api):
    data = {
        'email': 'test_client1@test.com',
        'password': 'testpassword'
    }
    response = api.post('/login', json=data)
    
    token = response.json()['access_token']
    
    data = {'user_id_to_follow': 2}
    response = api.delete('/unfollow',
                          headers={'Authorization': token},
                          json=data)
    assert response.status_code == 400, response.text
    
    data = {'user_id_to_follow': 2}
    response = api.put('/follow',
                       headers={'Authorization': token},
                       json=data)
    assert response.status_code == 200, response.text
    
    data = {'user_id_to_follow': 2}
    response = api.delete('/unfollow',
                          headers={'Authorization': token},
                          json=data)
    assert response.status_code == 200, response.text


def test_timeline(api):
    data = {
        'email': 'test_client1@test.com',
        'password': 'testpassword'
    }
    response = api.post('/login', json=data)
    
    token = response.json()['access_token']
    response = api.get('/timeline', headers={'Authorization': token})
    assert response.status_code == 200, response.text
    
    timeline = response.json()['timeline']
    assert len(timeline) != 0, timeline
    assert timeline[0]['tweet'] == 'HELLO WORLD!', timeline[0]['tweet']
