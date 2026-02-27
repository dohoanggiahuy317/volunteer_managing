from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request, url_for, g
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

app = Flask(
    __name__,
    static_folder=str(ROOT_DIR / "frontend" / "static"),
    template_folder=str(ROOT_DIR / "frontend" / "templates"),
)
CORS(app, resources={r"/*": {"origins": "*"}})

# Global store following the new normalized schema
store: dict[str, list[dict[str, Any]]] = {
    "users": [],
    "roles": [],
    "user_roles": [],
    "pantries": [],
    "pantry_leads": [],
    "shifts": [],
    "shift_roles": [],
    "shift_signups": [],
}

next_shift_id = 1
next_shift_role_id = 1
next_signup_id = 1

# Mock current user (no auth yet): default to user id=4 (admin)
DEFAULT_USER_ID = 4


def load_seed_data() -> None:
    global store, next_shift_id, next_shift_role_id, next_signup_id
    data_path = Path(__file__).resolve().parent / "data" / "db.json"
    if data_path.exists():
        data = json.loads(data_path.read_text(encoding="utf-8"))
        store = {
            "users": list(data.get("users", [])),
            "roles": list(data.get("roles", [])),
            "user_roles": list(data.get("user_roles", [])),
            "pantries": list(data.get("pantries", [])),
            "pantry_leads": list(data.get("pantry_leads", [])),
            "shifts": list(data.get("shifts", [])),
            "shift_roles": list(data.get("shift_roles", [])),
            "shift_signups": list(data.get("shift_signups", [])),
        }
        if store["shifts"]:
            next_shift_id = max(s.get("shift_id", 0) for s in store["shifts"]) + 1
        if store["shift_roles"]:
            next_shift_role_id = max(sr.get("shift_role_id", 0) for sr in store["shift_roles"]) + 1
        if store["shift_signups"]:
            next_signup_id = max(su.get("signup_id", 0) for su in store["shift_signups"]) + 1


load_seed_data()


@app.before_request
def set_current_user() -> None:
    """Allow switching user via ?user_id=X query parameter for testing."""
    user_id = request.args.get("user_id", type=int) or DEFAULT_USER_ID
    g.current_user_id = user_id


def find_user_by_id(user_id: int) -> dict[str, Any] | None:
    return next((u for u in store["users"] if u.get("user_id") == user_id), None)


def get_user_roles(user_id: int) -> list[str]:
    """Get all role names for a user."""
    role_ids = [
        ur.get("role_id")
        for ur in store["user_roles"]
        if ur.get("user_id") == user_id
    ]
    return [
        r.get("role_name")
        for r in store["roles"]
        if r.get("role_id") in role_ids
    ]


def user_has_role(user_id: int, role_name: str) -> bool:
    """Check if user has a specific role."""
    return role_name in get_user_roles(user_id)


def current_user() -> dict[str, Any] | None:
    user_id = getattr(g, "current_user_id", DEFAULT_USER_ID)
    return find_user_by_id(user_id)


def find_pantry_by_id(pantry_id: int) -> dict[str, Any] | None:
    return next((p for p in store["pantries"] if p.get("pantry_id") == pantry_id), None)


def pantries_for_current_user() -> list[dict[str, Any]]:
    """Pantries the current user leads (or all if ADMIN)."""
    user = current_user()
    if not user:
        return []
    user_id = user.get("user_id")
    
    if user_has_role(user_id, "ADMIN"):
        return list(store["pantries"])
    
    if user_has_role(user_id, "PANTRY_LEAD"):
        pantry_ids = [
            pl.get("pantry_id")
            for pl in store["pantry_leads"]
            if pl.get("user_id") == user_id
        ]
        return [p for p in store["pantries"] if p.get("pantry_id") in pantry_ids]
    
    return []


def get_pantry_leads(pantry_id: int) -> list[dict[str, Any]]:
    """Get all lead users for a pantry."""
    lead_user_ids = [
        pl.get("user_id")
        for pl in store["pantry_leads"]
        if pl.get("pantry_id") == pantry_id
    ]
    return [u for u in store["users"] if u.get("user_id") in lead_user_ids]


def get_shift_roles(shift_id: int) -> list[dict[str, Any]]:
    """Get all shift roles for a shift."""
    return [sr for sr in store["shift_roles"] if sr.get("shift_id") == shift_id]


def get_shift_signups(shift_role_id: int) -> list[dict[str, Any]]:
    """Get all signups for a shift role."""
    return [ss for ss in store["shift_signups"] if ss.get("shift_role_id") == shift_role_id]


# ========== API ROUTES ==========

@app.get("/api/me")
def get_current_user() -> Any:
    """Get current logged-in user with roles."""
    user = current_user()
    if not user:
        return jsonify({"error": "No user"}), 401
    roles = get_user_roles(user.get("user_id"))
    resp = dict(user)
    resp["roles"] = roles
    return jsonify(resp)


@app.get("/api/users")
def list_users() -> Any:
    """List all users (ADMIN only). Optional role filter: ?role=PANTRY_LEAD."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403

    users = list(store["users"])
    role_filter = request.args.get("role")
    
    if role_filter:
        filtered_users = []
        for u in users:
            if user_has_role(u.get("user_id"), role_filter):
                filtered_users.append(u)
        users = filtered_users
    
    # Enrich with roles
    for u in users:
        u["roles"] = get_user_roles(u.get("user_id"))
    
    return jsonify(users)


@app.get("/api/roles")
def list_roles() -> Any:
    """List all available roles."""
    return jsonify(store["roles"])


@app.post("/api/users")
def create_user() -> Any:
    """Create a new user (ADMIN only)."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    required = ["full_name", "email", "password_hash"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    # Check email uniqueness
    if any(u.get("email") == payload["email"] for u in store["users"]):
        return jsonify({"error": "Email already exists"}), 400

    user_id = (max((u.get("user_id", 0) for u in store["users"]), default=0) + 1)
    new_user = {
        "user_id": user_id,
        "full_name": payload["full_name"],
        "email": payload["email"],
        "password_hash": payload["password_hash"],
        "is_active": payload.get("is_active", True),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    store["users"].append(new_user)
    
    # Assign roles if provided
    roles = payload.get("roles", [])
    for role_name in roles:
        role = next((r for r in store["roles"] if r.get("role_name") == role_name), None)
        if role:
            store["user_roles"].append({
                "user_id": user_id,
                "role_id": role.get("role_id"),
            })
    
    new_user["roles"] = roles
    return jsonify(new_user), 201


@app.get("/api/pantries")
def list_pantries() -> Any:
    """List pantries accessible to current user."""
    pantries = pantries_for_current_user()
    for p in pantries:
        p["leads"] = get_pantry_leads(p.get("pantry_id"))
    return jsonify(pantries)


@app.get("/api/pantries/<int:pantry_id>")
def get_pantry(pantry_id: int) -> Any:
    """Get pantry by ID."""
    allowed = {p.get("pantry_id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    
    pantry = find_pantry_by_id(pantry_id)
    if not pantry:
        return jsonify({"error": "Not found"}), 404
    
    pantry["leads"] = get_pantry_leads(pantry_id)
    return jsonify(pantry)


@app.post("/api/pantries")
def create_pantry() -> Any:
    """Create a new pantry (ADMIN only)."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    required = ["name", "location_address"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    pantry_id = max((p.get("pantry_id", 0) for p in store["pantries"]), default=0) + 1
    new_pantry = {
        "pantry_id": pantry_id,
        "name": payload["name"],
        "location_address": payload["location_address"],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    store["pantries"].append(new_pantry)
    
    # Assign leads if provided
    lead_ids = payload.get("lead_ids", [])
    for lead_id in lead_ids:
        lead = find_user_by_id(lead_id)
        if lead and user_has_role(lead_id, "PANTRY_LEAD"):
            # Check if not already a lead
            if not any(
                pl.get("pantry_id") == pantry_id and pl.get("user_id") == lead_id
                for pl in store["pantry_leads"]
            ):
                store["pantry_leads"].append({
                    "pantry_id": pantry_id,
                    "user_id": lead_id,
                })
    
    new_pantry["leads"] = get_pantry_leads(pantry_id)
    return jsonify(new_pantry), 201


@app.post("/api/pantries/<int:pantry_id>/leads")
def add_pantry_lead(pantry_id: int) -> Any:
    """Assign a pantry lead to a pantry (ADMIN only)."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403

    pantry = find_pantry_by_id(pantry_id)
    if not pantry:
        return jsonify({"error": "Pantry not found"}), 404

    payload = request.get_json(silent=True) or {}
    lead_id = payload.get("user_id")
    
    if not lead_id:
        return jsonify({"error": "Missing user_id"}), 400

    lead = find_user_by_id(lead_id)
    if not lead or not user_has_role(lead_id, "PANTRY_LEAD"):
        return jsonify({"error": "User must have PANTRY_LEAD role"}), 400

    # Check if already a lead
    if any(
        pl.get("pantry_id") == pantry_id and pl.get("user_id") == lead_id
        for pl in store["pantry_leads"]
    ):
        return jsonify({"error": "User already a lead for this pantry"}), 400

    store["pantry_leads"].append({
        "pantry_id": pantry_id,
        "user_id": lead_id,
    })

    return jsonify({
        "pantry_id": pantry_id,
        "user_id": lead_id,
        "user": lead,
    }), 201


@app.delete("/api/pantries/<int:pantry_id>/leads/<int:lead_id>")
def remove_pantry_lead(pantry_id: int, lead_id: int) -> Any:
    """Remove a pantry lead from a pantry (ADMIN only)."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403

    pantry = find_pantry_by_id(pantry_id)
    if not pantry:
        return jsonify({"error": "Pantry not found"}), 404

    lead = find_user_by_id(lead_id)
    if not lead:
        return jsonify({"error": "User not found"}), 404

    # Find and remove
    store["pantry_leads"] = [
        pl for pl in store["pantry_leads"]
        if not (pl.get("pantry_id") == pantry_id and pl.get("user_id") == lead_id)
    ]

    return jsonify({"success": True}), 200


# ========== SHIFTS ==========

@app.get("/api/pantries/<int:pantry_id>/shifts")
def get_shifts(pantry_id: int) -> Any:
    """Get all shifts for a pantry."""
    allowed = {p.get("pantry_id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    
    shifts = [s for s in store["shifts"] if s.get("pantry_id") == pantry_id]
    
    # Enrich with shift_roles
    for shift in shifts:
        shift["roles"] = get_shift_roles(shift.get("shift_id"))
    
    return jsonify(shifts)


@app.post("/api/pantries/<int:pantry_id>/shifts")
def create_shift(pantry_id: int) -> Any:
    """Create a new shift (PANTRY_LEAD or ADMIN)."""
    global next_shift_id
    
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    is_lead = user_has_role(user_id, "PANTRY_LEAD")
    
    if not (is_admin or is_lead):
        return jsonify({"error": "Forbidden"}), 403
    
    # If PANTRY_LEAD, check if leads this pantry
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Not a lead for this pantry"}), 403

    pantry = find_pantry_by_id(pantry_id)
    if not pantry:
        return jsonify({"error": "Pantry not found"}), 404

    payload = request.get_json(silent=True) or {}
    required = ["shift_name", "start_time", "end_time"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    new_shift = {
        "shift_id": next_shift_id,
        "pantry_id": pantry_id,
        "shift_name": payload["shift_name"],
        "start_time": payload["start_time"],
        "end_time": payload["end_time"],
        "status": payload.get("status", "OPEN"),
        "created_by": user_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    next_shift_id += 1
    store["shifts"].append(new_shift)
    
    new_shift["roles"] = []
    return jsonify(new_shift), 201


@app.get("/api/shifts/<int:shift_id>")
def get_shift(shift_id: int) -> Any:
    """Get a single shift with its roles."""
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_id), None)
    if not shift:
        return jsonify({"error": "Not found"}), 404
    
    # Check permission
    pantry_id = shift.get("pantry_id")
    allowed = {p.get("pantry_id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    
    shift["roles"] = get_shift_roles(shift_id)
    return jsonify(shift)


@app.patch("/api/shifts/<int:shift_id>")
def update_shift(shift_id: int) -> Any:
    """Update shift (PANTRY_LEAD or ADMIN)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_id), None)
    if not shift:
        return jsonify({"error": "Not found"}), 404
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    pantry_id = shift.get("pantry_id")
    
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    
    if "shift_name" in payload:
        shift["shift_name"] = payload["shift_name"]
    if "start_time" in payload:
        shift["start_time"] = payload["start_time"]
    if "end_time" in payload:
        shift["end_time"] = payload["end_time"]
    if "status" in payload:
        shift["status"] = payload["status"]
    
    shift["updated_at"] = datetime.utcnow().isoformat() + "Z"
    shift["roles"] = get_shift_roles(shift_id)
    
    return jsonify(shift)


@app.delete("/api/shifts/<int:shift_id>")
def delete_shift(shift_id: int) -> Any:
    """Delete a shift (PANTRY_LEAD or ADMIN)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_id), None)
    if not shift:
        return jsonify({"error": "Not found"}), 404
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    pantry_id = shift.get("pantry_id")
    
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Forbidden"}), 403

    # Delete associated shift_roles and signups
    shift_role_ids = [sr.get("shift_role_id") for sr in store["shift_roles"] if sr.get("shift_id") == shift_id]
    store["shift_signups"] = [ss for ss in store["shift_signups"] if ss.get("shift_role_id") not in shift_role_ids]
    store["shift_roles"] = [sr for sr in store["shift_roles"] if sr.get("shift_id") != shift_id]
    store["shifts"] = [s for s in store["shifts"] if s.get("shift_id") != shift_id]

    return jsonify({"success": True}), 200


# ========== SHIFT ROLES ==========

@app.post("/api/shifts/<int:shift_id>/roles")
def create_shift_role(shift_id: int) -> Any:
    """Create a role/position within a shift."""
    global next_shift_role_id
    
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_id), None)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    pantry_id = shift.get("pantry_id")
    
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    required = ["role_title", "required_count"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    try:
        required_count = int(payload["required_count"])
        if required_count < 1:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "required_count must be >= 1"}), 400

    new_shift_role = {
        "shift_role_id": next_shift_role_id,
        "shift_id": shift_id,
        "role_title": payload["role_title"],
        "required_count": required_count,
        "filled_count": 0,
        "status": "OPEN",
    }
    next_shift_role_id += 1
    store["shift_roles"].append(new_shift_role)

    return jsonify(new_shift_role), 201


@app.patch("/api/shift-roles/<int:shift_role_id>")
def update_shift_role(shift_role_id: int) -> Any:
    """Update a shift role (PANTRY_LEAD or ADMIN)."""
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    shift_role = next((sr for sr in store["shift_roles"] if sr.get("shift_role_id") == shift_role_id), None)
    if not shift_role:
        return jsonify({"error": "Not found"}), 404
    
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_role.get("shift_id")), None)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    pantry_id = shift.get("pantry_id")
    
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    
    if "role_title" in payload:
        shift_role["role_title"] = payload["role_title"]
    if "required_count" in payload:
        try:
            required_count = int(payload["required_count"])
            if required_count < 1:
                raise ValueError
            shift_role["required_count"] = required_count
        except (TypeError, ValueError):
            return jsonify({"error": "required_count must be >= 1"}), 400
    if "status" in payload:
        shift_role["status"] = payload["status"]

    return jsonify(shift_role)


@app.delete("/api/shift-roles/<int:shift_role_id>")
def delete_shift_role(shift_role_id: int) -> Any:
    """Delete a shift role and its signups."""
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    shift_role = next((sr for sr in store["shift_roles"] if sr.get("shift_role_id") == shift_role_id), None)
    if not shift_role:
        return jsonify({"error": "Not found"}), 404
    
    shift = next((s for s in store["shifts"] if s.get("shift_id") == shift_role.get("shift_id")), None)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404
    
    user_id = user.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    pantry_id = shift.get("pantry_id")
    
    if not is_admin:
        if not any(
            pl.get("pantry_id") == pantry_id and pl.get("user_id") == user_id
            for pl in store["pantry_leads"]
        ):
            return jsonify({"error": "Forbidden"}), 403

    # Delete signups for this role
    store["shift_signups"] = [ss for ss in store["shift_signups"] if ss.get("shift_role_id") != shift_role_id]
    store["shift_roles"] = [sr for sr in store["shift_roles"] if sr.get("shift_role_id") != shift_role_id]

    return jsonify({"success": True}), 200


# ========== SHIFT SIGNUPS ==========

@app.post("/api/shift-roles/<int:shift_role_id>/signup")
def create_signup(shift_role_id: int) -> Any:
    """Volunteer signs up for a shift role."""
    global next_signup_id
    
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "VOLUNTEER"):
        return jsonify({"error": "Forbidden or not a volunteer"}), 403
    
    shift_role = next((sr for sr in store["shift_roles"] if sr.get("shift_role_id") == shift_role_id), None)
    if not shift_role:
        return jsonify({"error": "Shift role not found"}), 404

    payload = request.get_json(silent=True) or {}
    payload_user_id = payload.get("user_id")
    
    # Users can only sign themselves up, unless authenticated (future)
    user_id = payload_user_id or user.get("user_id")

    # Prevent duplicate signups
    if any(
        ss.get("shift_role_id") == shift_role_id and ss.get("user_id") == user_id
        for ss in store["shift_signups"]
    ):
        return jsonify({"error": "Already signed up"}), 400

    # Check capacity
    if shift_role.get("filled_count", 0) >= shift_role.get("required_count", 0):
        return jsonify({"error": "This role is full"}), 400

    new_signup = {
        "signup_id": next_signup_id,
        "shift_role_id": shift_role_id,
        "user_id": user_id,
        "signup_status": payload.get("signup_status", "CONFIRMED"),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    next_signup_id += 1
    store["shift_signups"].append(new_signup)

    # Update filled_count
    shift_role["filled_count"] = shift_role.get("filled_count", 0) + 1
    if shift_role["filled_count"] >= shift_role.get("required_count", 0):
        shift_role["status"] = "FULL"

    user_obj = find_user_by_id(user_id)
    return jsonify({**new_signup, "user": user_obj}), 201


@app.get("/api/shift-roles/<int:shift_role_id>/signups")
def get_signups_for_role(shift_role_id: int) -> Any:
    """Get all signups for a shift role."""
    shift_role = next((sr for sr in store["shift_roles"] if sr.get("shift_role_id") == shift_role_id), None)
    if not shift_role:
        return jsonify({"error": "Not found"}), 404
    
    signups = get_shift_signups(shift_role_id)
    
    # Enrich with user info
    for signup in signups:
        signup["user"] = find_user_by_id(signup.get("user_id"))
    
    return jsonify(signups)


@app.delete("/api/signups/<int:signup_id>")
def delete_signup(signup_id: int) -> Any:
    """Cancel a signup."""
    user = current_user()
    if not user:
        return jsonify({"error": "Forbidden"}), 403
    
    signup = next((ss for ss in store["shift_signups"] if ss.get("signup_id") == signup_id), None)
    if not signup:
        return jsonify({"error": "Not found"}), 404
    
    user_id = user.get("user_id")
    signup_user_id = signup.get("user_id")
    is_admin = user_has_role(user_id, "ADMIN")
    
    # Only the signup user or admin can delete
    if user_id != signup_user_id and not is_admin:
        return jsonify({"error": "Forbidden"}), 403

    shift_role_id = signup.get("shift_role_id")
    shift_role = next((sr for sr in store["shift_roles"] if sr.get("shift_role_id") == shift_role_id), None)
    
    store["shift_signups"] = [ss for ss in store["shift_signups"] if ss.get("signup_id") != signup_id]
    
    # Update filled_count
    if shift_role:
        shift_role["filled_count"] = max(0, shift_role.get("filled_count", 0) - 1)
        if shift_role["filled_count"] < shift_role.get("required_count", 0):
            shift_role["status"] = "OPEN"

    return jsonify({"success": True}), 200


@app.patch("/api/signups/<int:signup_id>")
def update_signup(signup_id: int) -> Any:
    """Update signup status (ADMIN only - change status to NO_SHOW, etc)."""
    user = current_user()
    if not user or not user_has_role(user.get("user_id"), "ADMIN"):
        return jsonify({"error": "Forbidden"}), 403
    
    signup = next((ss for ss in store["shift_signups"] if ss.get("signup_id") == signup_id), None)
    if not signup:
        return jsonify({"error": "Not found"}), 404
    
    payload = request.get_json(silent=True) or {}
    if "signup_status" in payload:
        signup["signup_status"] = payload["signup_status"]

    return jsonify(signup)


# ========== PUBLIC ==========

@app.get("/api/public/pantries/<slug>/shifts")
def get_public_shifts(slug: str) -> Any:
    """Public endpoint: get shifts for a pantry (no auth)."""
    # Find pantry by slug (store pantry name or id as slug)
    pantry = next((p for p in store["pantries"] if str(p.get("pantry_id")) == slug or p.get("name", "").lower().replace(" ", "-") == slug), None)
    
    if not pantry:
        return jsonify([])
    
    pantry_id = pantry.get("pantry_id")
    shifts = [s for s in store["shifts"] if s.get("pantry_id") == pantry_id and s.get("status") != "CANCELLED"]
    
    # Enrich with roles
    for shift in shifts:
        shift["roles"] = get_shift_roles(shift.get("shift_id"))
    
    return jsonify(shifts)


# ========== PAGES ==========

@app.get("/")
def index() -> Any:
    """Main dashboard - unified page for all roles."""
    return render_template("dashboard.html")


@app.get("/dashboard")
def dashboard() -> Any:
    """Main dashboard - unified page for all roles."""
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
