import pytest
from fastapi.testclient import TestClient

from rideops.api.app import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path / "rideops-test.db"))
