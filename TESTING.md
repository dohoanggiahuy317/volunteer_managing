# Testing the Super Admin Pantry Assignment Feature

## Users in the System

- **User ID 1**: courtney@licking-county-pantry.org (PANTRY_LEAD) - has 1 pantry assigned
- **User ID 2**: james@northside-pantry.org (PANTRY_LEAD) - has 1 pantry assigned  
- **User ID 3**: maria@southpoint-pantry.org (PANTRY_LEAD) - no pantry assigned yet
- **User ID 4**: super@example.org (SUPER_ADMIN) - can assign pantries

## Switching Users (for Development)

Add `?user_id=X` to any API request to switch users. Example:

```bash
# View as super admin (default)
curl http://localhost:5000/api/me

# View as pantry lead with ID 1
curl http://localhost:5000/api/me?user_id=1

# Get pantries visible to user 1
curl http://localhost:5000/api/pantries?user_id=1

# Get pantries visible to super admin
curl http://localhost:5000/api/pantries?user_id=4
```

## Frontend URLs

- **Super Admin Panel**: `http://localhost:5173/super-admin/assignments?user_id=4`
- **Pantry Lead 1**: `http://localhost:5173/lead/shifts?user_id=1`
- **Pantry Lead 3** (unassigned): `http://localhost:5173/lead/shifts?user_id=3`

## Testing the Flow

1. Go to super admin panel: `http://localhost:5173/super-admin/assignments?user_id=4`
2. Use the dropdown to assign "Southpoint Pantry" to a pantry lead
3. Switch to that lead's view (e.g., `?user_id=3`) and verify they can now see the pantry

## Database Schema

The pantry now has a `lead_id` field that links to a user:

```json
{
  "id": 1,
  "name": "Licking County Pantry",
  "slug": "licking-county-pantry",
  "lead_id": 1
}
```

- `lead_id: null` = unassigned pantry
- `lead_id: integer` = pantry assigned to that user

## Authorization Rules

- **SUPER_ADMIN**: Can see all pantries and assign/reassign them
- **PANTRY_LEAD**: Can only see and manage pantries where `lead_id` equals their user ID
