# volunteer_managing

Volunteer and shift management for food pantries. Pantry leads create shifts; public users view shifts by pantry slug.

## Roles

- **SUPER_ADMIN** – Can create pantries (future).
- **PANTRY_LEAD** – Can create shifts for pantries they lead (1 lead : many pantries; each pantry has 1 lead).
- **VOLUNTEER** – Can sign up for shifts (future).

## Run

### Development

1. **Backend (Flask)** – from repo root:
   ```bash
   cd backend && pip install -r requirements.txt && python app.py
   ```
   API: `http://localhost:5000/api/...`

2. **Frontend (Vite)** – in another terminal:
   ```bash
   cd frontend && npm install && npm run dev
   ```
   App: `http://localhost:5173` — proxy sends `/api` to Flask.

### Production (single server)

1. Build frontend: `cd frontend && npm run build`
2. Run Flask: `cd backend && python app.py`
3. Open `http://localhost:5000` — Flask serves the React app and `/api/*`.

## Public shifts

No login: `http://localhost:5000/pantries/licking-county-pantry/shifts` (or via Vite dev with same path).
