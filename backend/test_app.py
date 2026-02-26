import pytest
from app import app, store, load_seed_data, DEFAULT_USER_ID


@pytest.fixture
def client():
    """Create a test client with fresh app context."""
    app.config['TESTING'] = True
    with app.app_context():
        # Reset store before each test
        load_seed_data()
        yield app.test_client()


@pytest.fixture
def super_admin_query():
    """Query param for super admin requests."""
    return {'user_id': 4}


@pytest.fixture
def lead1_query():
    """Query param for pantry lead 1 requests."""
    return {'user_id': 1}


@pytest.fixture
def lead2_query():
    """Query param for pantry lead 2 requests."""
    return {'user_id': 2}


@pytest.fixture
def lead3_query():
    """Query param for pantry lead 3 requests (unassigned)."""
    return {'user_id': 3}


class TestUserManagement:
    """Test user and authentication endpoints."""

    def test_get_current_user_super_admin(self, client, super_admin_query):
        """Super admin can get their own user info."""
        r = client.get('/api/me', query_string=super_admin_query)
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 4
        assert data['role'] == 'SUPER_ADMIN'
        assert 'super@example.org' in data['email']

    def test_get_current_user_pantry_lead(self, client, lead1_query):
        """Pantry lead can get their own user info."""
        r = client.get('/api/me', query_string=lead1_query)
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1
        assert data['role'] == 'PANTRY_LEAD'

    def test_list_users_super_admin_only(self, client, lead1_query, super_admin_query):
        """Only super admin can list users."""
        # Pantry lead cannot list users
        r = client.get('/api/users', query_string=lead1_query)
        assert r.status_code == 403
        assert r.get_json()['error'] == 'Forbidden'

        # Super admin can list all users
        r = client.get('/api/users', query_string=super_admin_query)
        assert r.status_code == 200
        users = r.get_json()
        assert len(users) == 4
        assert any(u['id'] == 4 and u['role'] == 'SUPER_ADMIN' for u in users)

    def test_list_users_with_role_filter(self, client, super_admin_query):
        """Super admin can filter users by role."""
        r = client.get(
            '/api/users',
            query_string={**super_admin_query, 'role': 'PANTRY_LEAD'}
        )
        assert r.status_code == 200
        users = r.get_json()
        assert len(users) == 3
        assert all(u['role'] == 'PANTRY_LEAD' for u in users)


class TestPantryVisibility:
    """Test pantry visibility based on user roles."""

    def test_super_admin_sees_all_pantries(self, client, super_admin_query):
        """Super admin can see all pantries."""
        r = client.get('/api/pantries', query_string=super_admin_query)
        assert r.status_code == 200
        pantries = r.get_json()
        assert len(pantries) == 3
        ids = {p['id'] for p in pantries}
        assert ids == {1, 2, 3}

    def test_pantry_lead_sees_assigned_pantries_only(self, client, lead1_query, lead3_query):
        """Pantry lead only sees pantries assigned to them."""
        # Lead 1 has 1 pantry assigned
        r = client.get('/api/pantries', query_string=lead1_query)
        assert r.status_code == 200
        pantries = r.get_json()
        assert len(pantries) == 1
        assert pantries[0]['id'] == 1
        assert pantries[0]['lead_id'] == 1

        # Lead 3 has no pantries assigned
        r = client.get('/api/pantries', query_string=lead3_query)
        assert r.status_code == 200
        pantries = r.get_json()
        assert len(pantries) == 0

    def test_get_pantry_by_id_permission_check(self, client, lead1_query, lead3_query, super_admin_query):
        """Pantry access checks permissions."""
        # Lead 1 can get pantry 1 (assigned to them)
        r = client.get('/api/pantries/1', query_string=lead1_query)
        assert r.status_code == 200
        assert r.get_json()['id'] == 1

        # Lead 3 cannot get pantry 1 (not assigned to them)
        r = client.get('/api/pantries/1', query_string=lead3_query)
        assert r.status_code == 403

        # Super admin can get any pantry
        r = client.get('/api/pantries/3', query_string=super_admin_query)
        assert r.status_code == 200
        assert r.get_json()['id'] == 3

    def test_get_pantry_by_slug(self, client):
        """Get pantry by slug returns correct pantry."""
        r = client.get('/api/pantries/slug/licking-county-pantry')
        assert r.status_code == 200
        data = r.get_json()
        assert data['id'] == 1
        assert data['name'] == 'Licking County Pantry'

    def test_get_nonexistent_pantry(self, client, super_admin_query):
        """Getting nonexistent pantry returns 404."""
        r = client.get('/api/pantries/999', query_string=super_admin_query)
        assert r.status_code == 404


class TestPantryAssignment:
    """Test pantry assignment by super admin."""

    def test_super_admin_can_assign_pantry(self, client, super_admin_query, lead3_query):
        """Super admin can assign an unassigned pantry to a lead."""
        # Verify lead 3 initially has no pantries
        r = client.get('/api/pantries', query_string=lead3_query)
        assert len(r.get_json()) == 0

        # Super admin assigns pantry 3 to lead 3
        r = client.patch(
            '/api/pantries/3',
            json={'lead_id': 3},
            query_string=super_admin_query
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data['lead_id'] == 3

        # Now lead 3 can see the pantry
        r = client.get('/api/pantries', query_string=lead3_query)
        pantries = r.get_json()
        assert len(pantries) == 1
        assert pantries[0]['id'] == 3

    def test_super_admin_can_reassign_pantry(self, client, super_admin_query, lead1_query, lead2_query):
        """Super admin can reassign a pantry from one lead to another."""
        # Lead 1 initially has pantry 1
        r = client.get('/api/pantries', query_string=lead1_query)
        assert len(r.get_json()) == 1

        # Super admin reassigns pantry 1 to lead 2
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': 2},
            query_string=super_admin_query
        )
        assert r.status_code == 200
        assert r.get_json()['lead_id'] == 2

        # Lead 1 no longer sees pantry 1
        r = client.get('/api/pantries', query_string=lead1_query)
        assert len(r.get_json()) == 0

        # Lead 2 now sees both pantries 1 and 2
        r = client.get('/api/pantries', query_string=lead2_query)
        pantries = r.get_json()
        assert len(pantries) == 2
        ids = {p['id'] for p in pantries}
        assert ids == {1, 2}

    def test_super_admin_can_unassign_pantry(self, client, super_admin_query, lead1_query):
        """Super admin can unassign a pantry by setting lead_id to null."""
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': None},
            query_string=super_admin_query
        )
        assert r.status_code == 200
        assert r.get_json()['lead_id'] is None

        # Lead 1 no longer sees it
        r = client.get('/api/pantries', query_string=lead1_query)
        assert len(r.get_json()) == 0

    def test_only_super_admin_can_assign(self, client, lead1_query):
        """Only super admin can assign pantries."""
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': 2},
            query_string=lead1_query
        )
        assert r.status_code == 403
        assert r.get_json()['error'] == 'Forbidden'

    def test_cannot_assign_to_invalid_lead(self, client, super_admin_query):
        """Cannot assign pantry to non-existent or non-lead user."""
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': 999},
            query_string=super_admin_query
        )
        assert r.status_code == 400
        assert r.get_json()['error'] == 'Invalid lead_id'

    def test_cannot_assign_to_super_admin(self, client, super_admin_query):
        """Cannot assign pantry to super admin user."""
        r = client.patch(
            '/api/pantries/1',
            json={'lead_id': 4},  # super admin
            query_string=super_admin_query
        )
        assert r.status_code == 400
        assert r.get_json()['error'] == 'Invalid lead_id'


class TestShifts:
    """Test shift creation and retrieval."""

    def test_create_shift_success(self, client, lead1_query):
        """Pantry lead can create a shift in their pantry."""
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 2,
        }
        r = client.post(
            '/api/pantries/1/shifts',
            json=payload,
            query_string=lead1_query
        )
        assert r.status_code == 201
        data = r.get_json()
        assert data['shift_id'] == 1
        assert data['role_name'] == 'Cashier'
        assert data['filled_count'] == 0
        assert data['status'] == 'Open'

    def test_create_shift_missing_fields(self, client, lead1_query):
        """Creating shift with missing fields returns 400."""
        r = client.post(
            '/api/pantries/1/shifts',
            json={'role_name': 'Cashier'},  # missing other fields
            query_string=lead1_query
        )
        assert r.status_code == 400
        assert 'Missing fields' in r.get_json()['error']

    def test_create_shift_invalid_required_count(self, client, lead1_query):
        """Creating shift with invalid required_count returns 400."""
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 0,  # invalid
        }
        r = client.post(
            '/api/pantries/1/shifts',
            json=payload,
            query_string=lead1_query
        )
        assert r.status_code == 400

    def test_create_shift_permission_check(self, client, lead3_query):
        """Pantry lead without access cannot create shift."""
        payload = {
            'role_name': 'Cashier',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 2,
        }
        r = client.post(
            '/api/pantries/1/shifts',
            json=payload,
            query_string=lead3_query
        )
        assert r.status_code == 403

    def test_get_shifts_for_pantry(self, client, lead1_query, super_admin_query):
        """Can retrieve shifts for a pantry."""
        # Create two shifts
        for i in range(2):
            payload = {
                'role_name': f'Role {i}',
                'start_time': '2026-03-01T09:00:00Z',
                'end_time': '2026-03-01T17:00:00Z',
                'required_count': 1,
            }
            client.post('/api/pantries/1/shifts', json=payload, query_string=lead1_query)

        # Get shifts for pantry 1
        r = client.get('/api/pantries/1/shifts', query_string=super_admin_query)
        assert r.status_code == 200
        shifts = r.get_json()
        assert len(shifts) == 2

    def test_get_shifts_permission_check(self, client, lead3_query):
        """Only authorized users can get shifts for a pantry."""
        r = client.get('/api/pantries/1/shifts', query_string=lead3_query)
        assert r.status_code == 403

    def test_public_shifts_endpoint(self, client):
        """Public can view shifts for a pantry by slug."""
        # Create a shift
        payload = {
            'role_name': 'Volunteer',
            'start_time': '2026-03-01T09:00:00Z',
            'end_time': '2026-03-01T17:00:00Z',
            'required_count': 3,
        }
        client.post('/api/pantries/1/shifts', json=payload, query_string={'user_id': 1})

        # Public can see shifts via slug (no auth needed)
        r = client.get('/api/public/pantries/licking-county-pantry/shifts')
        assert r.status_code == 200
        shifts = r.get_json()
        assert len(shifts) == 1
        assert shifts[0]['role_name'] == 'Volunteer'


class TestDataLoading:
    """Test that seed data loads correctly."""

    def test_db_json_loaded(self, client):
        """Verify db.json data is loaded into store."""
        r = client.get('/api/me', query_string={'user_id': 1})
        assert r.status_code == 200
        data = r.get_json()
        assert data['email'] == 'courtney@licking-county-pantry.org'

    def test_pantries_have_correct_structure(self, client, super_admin_query):
        """Verify pantries have expected fields."""
        r = client.get('/api/pantries', query_string=super_admin_query)
        pantries = r.get_json()
        assert len(pantries) >= 3
        for p in pantries:
            assert 'id' in p
            assert 'name' in p
            assert 'slug' in p
            assert 'lead_id' in p
