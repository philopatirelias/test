from fastapi.testclient import TestClient
from main import app


def test_health():
    c = TestClient(app)
    r = c.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_session_demo_state_delete_flow():
    c = TestClient(app)
    s = c.post('/sessions', json={'consult_type': 'internal_medicine'}).json()['session_id']
    r = c.post(f'/sessions/{s}/demo-transcript', json={'text': 'Patient: chest discomfort after meals'})
    assert r.status_code == 200
    state = c.get(f'/sessions/{s}/state')
    assert state.status_code == 200
    body = state.json()
    assert 'transcript' in body and 'chest' in body['transcript']
    assert isinstance(body['suggestions'], list)
    d = c.delete(f'/sessions/{s}')
    assert d.status_code == 200
