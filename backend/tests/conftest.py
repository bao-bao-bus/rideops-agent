import pytest
from fastapi.testclient import TestClient

from rideops.api.app import app


@pytest.fixture()
def client():
    return TestClient(app)
