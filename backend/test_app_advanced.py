import pytest
from app import app, store, load_seed_data


@pytest.fixture
def client():
    """Create a test client with fresh app context."""
    app.config['TESTING'] = True
    with app.app_context():
        load_seed_data()
        yield app.test_client()


@pytest.fixture
def super_admin():
    return {'user_id': 4}


@pytest.fixture
def lead1():
    return {'user_id': 1}


@pytest.fixture
def lead2():
    return {'user_id': 2}


@pytest.fixture
def lead3():
    return {'user_id': 3}


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_multiple_sequential_assignments(self, client, super_admin, lead1, lead2, lead3):
        """Test reassigning pantry multiple times."""
        # Initial: pantry 1 → lead 1
        r = client.get('/api/pantries', query_string=lead1)
        assert len(r.get_json()) == 1

        # Reassign: pantry 1 → lead 2
        client.patch('/api/pantries/1', json={'lead_id': 2}, query_string=super_admin)
        r = client.get('/api/pantries', query_string=lead1)
        assert len(r.get_json()) == 0
        r = client.get('/api/pantries', query_string=lead2)
        assert len(r.get_json()) == 2

        # Reassign: pantry 1 → lead 3
        client.patch('/api/pantries/1', json={'lead_id': 3}, query_string=super_admin)
        r = client.get('/api/pantries', query_string=lead2)
        assert len(r.get_json()) == 1
        r = client.get('/api/pantries', query_string=lead3)
        assert len(r.get_json()) == 1

    def test_unassign_then_reassign(self, client, super_admin, lead1):
        """Test unassigning and then reassigning same pantry."""
        # Unassign
        r = client.patch('/api/pantries/1', json={'lead_id': None}, query_string=super_admin)
        assert r.get_json()['lead_id'] is None

        # Check lead no longer sees it
        r = client.get('/api/pantries', query_string=lead1)
        assert len(r.get_json()) == 0

        # Reassign
        r = client.patch('/api/pantries/1', json={'lead_id': 1}, query_string=super_admin)
        assert r.get_json()['lead_id'] == 1

        # Check lead sees it again
        r = client.get('/api/pantries', query_string=lead1)
        assert len(r.get_json()) == 1

    def test_create_multiple_shifts_auto_increment(self, client, lead1):
        """Test that shift IDs auto-increment correctly."""
        shift_ids = []
        for i in range(3):
            payload = {
                'role_name': f'Role {i}',
                'start_time': '2026-03-01T09:00:00Z',
                'end_time': '2026-03-01T17:00:00Z',
                'required_count': 1,
            }
            r = client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)
            shift_ids.append(r.get_json()['shift_id'])

        # IDs should be sequential
        assert shift_ids == [1, 2, 3]

    def test_shift_isolation_between_pantries(self, client, lead1, lead2):
        """Test that shifts in different pantries don't interfere."""
        # Lead 1 creates shift in pantry 1
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 1,
        }
        client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)

        # Lead 2 creates shift in pantry 2
        client.post('/api/pantries/2/shifts', json=payload, query_string=lead2)

        # Verify they're isolated
        r = client.get('/api/pantries/1/shifts', query_string=lead1)
        assert len(r.get_json()) == 1

        r = client.get('/api/pantries/2/shifts', query_string=lead2)
        assert len(r.get_json()) == 1

    def test_user_id_query_param_zero_uses_default(self, client, super_admin):
        """Test that user_id=0 falls back to DEFAULT_USER_ID."""
        r = client.get('/api/me', query_string={'user_id': 0})
        data = r.get_json()
        # Should fall back to DEFAULT_USER_ID (4 = super admin)
        assert data['role'] == 'SUPER_ADMIN'

    def test_empty_db_state_after_load(self, client):
        """Test handling of empty initial state."""
        with app.app_context():
            # This is already handled by load_seed_data fixture,
            # but verify it doesn't crash with empty store
            store['shifts'].clear()
            r = client.get('/api/pantries/1/shifts', query_string={'user_id': 1})
            assert r.status_code == 200
            assert r.get_json() == []


class TestJSONValidation:
    """Test JSON payload validation."""

    def test_malformed_json(self, client, lead1):
        """Test handling of malformed JSON."""
        r = client.post(
            '/api/pantries/1/shifts',
            data='not json',
            content_type='application/json',
            query_string=lead1
        )
        # Flask should handle this gracefully
        # get_json(silent=True) returns empty dict

    def test_extra_fields_ignored(self, client, lead1):
        """Test that extra fields in request are ignored."""
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 1,
            'extra_field': 'should be ignored',
            'another_field': 999,
        }
        r = client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)
        assert r.status_code == 201
        data = r.get_json()
        assert 'extra_field' not in data
        assert 'another_field' not in data

    def test_null_role_name(self, client, lead1):
        """Test that null role_name is rejected."""
        payload = {
            'role_name': None,
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 1,
        }
        r = client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)
        assert r.status_code == 400

    def test_string_required_count(self, client, lead1):
        """Test that string required_count type error is caught."""
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 'not a number',
        }
        r = client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)
        assert r.status_code == 400
        assert 'must be an integer' in r.get_json()['error']


class TestConcurrency:
    """Test concurrent-like operations."""

    def test_two_leads_accessing_same_unassigned_pantry(self, client, lead1, lead2):
        """Unassigned pantry shouldn't be visible to any lead."""
        # Unassign pantry 3
        client.patch('/api/pantries/3', json={'lead_id': None}, query_string={'user_id': 4})

        # Neither lead should see it
        r = client.get('/api/pantries', query_string=lead1)
        pantry_ids = {p['id'] for p in r.get_json()}
        assert 3 not in pantry_ids

        r = client.get('/api/pantries', query_string=lead2)
        pantry_ids = {p['id'] for p in r.get_json()}
        assert 3 not in pantry_ids

    def test_reassign_while_lead_creating_shift(self, client, lead1):
        """Test shift creation doesn't affect concurrent reassignment."""
        # Lead creates a shift
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 1,
        }
        r = client.post('/api/pantries/1/shifts', json=payload, query_string=lead1)
        assert r.status_code == 201
        shift_id = r.get_json()['shift_id']

        # Reassign pantry to different lead
        client.patch('/api/pantries/1', json={'lead_id': 2}, query_string={'user_id': 4})

        # Shift still exists in pantry
        r = client.get('/api/pantries/1/shifts', query_string={'user_id': 2})
        shifts = r.get_json()
        assert len(shifts) == 1
        assert shifts[0]['shift_id'] == shift_id


class TestDataErrors:
    """Test error responses with proper HTTP status codes."""

    def test_404_errors_are_consistent(self, client, super_admin):
        """Verify 404 responses are consistent."""
        endpoints = [
            '/api/pantries/999',
            '/api/pantries/slug/nonexistent-slug',
        ]
        for endpoint in endpoints:
            r = client.get(endpoint, query_string=super_admin)
            assert r.status_code == 404

    def test_403_errors_are_consistent(self, client, lead1, lead3):
        """Verify 403 forbidden responses are consistent."""
        # Lead 3 cannot access pantry 1
        r = client.get('/api/pantries/1', query_string=lead3)
        assert r.status_code == 403

        r = client.get('/api/pantries/1/shifts', query_string=lead3)
        assert r.status_code == 403

    def test_400_bad_request_errors(self, client, super_admin):
        """Verify 400 bad request responses."""
        # Invalid lead_id
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': 999},
            query_string=super_admin
        )
        assert r.status_code == 400

    def test_error_response_format(self, client, lead1):
        """Verify error responses have consistent format."""
        r = client.get('/api/pantries/999', query_string=lead1)
        assert r.status_code == 404
        data = r.get_json()
        assert 'error' in data
        assert isinstance(data['error'], str)
        assert len(data['error']) > 0


class TestSQL_InjectionLike:
    """Test that slug parameters are properly escaped."""

    def test_slug_with_special_chars(self, client):
        """Slug with special characters doesn't cause issues."""
        # This won't exist, but should return 404, not error
        r = client.get('/api/pantries/slug/test--pantry')
        assert r.status_code == 404

    def test_slug_unicode_handling(self, client):
        """Unicode in slug is handled safely."""
        r = client.get('/api/pantries/slug/café-pantry')
        assert r.status_code == 404
