import pytest
import os
import jwt
from datetime import datetime, timedelta, timezone

# Set testing environment variable
os.environ['TESTING'] = 'true'
os.environ['REDIS_PASSWORD'] = 'test-redis-pass'

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token():
    payload = {
        'user_id': 1,
        'username': 'testuser',
        'role': 'user',
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, 'super-secret-key', algorithm='HS256')

@pytest.fixture
def admin_token():
    payload = {
        'user_id': 99,
        'username': 'admin',
        'role': 'admin',
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, 'super-secret-key', algorithm='HS256')
