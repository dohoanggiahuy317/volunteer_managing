from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

store: dict[str, list[dict[str, Any]]] = {
    "users": [],
    "pantries": [],
    "shifts": [],
}
next_shift_id = 1

# Mock current user (no auth yet): default to user id=1 (first pantry lead)
DEFAULT_USER_ID = 4  # super admin for testing assignments


def load_seed_data() -> None:
    global store, next_shift_id
    for data_path in (
        Path(__file__).resolve().parent / "data" / "db.json",
        Path(__file__).resolve().parent.parent / "frontend" / "src" / "data" / "db.json",
    ):
        if data_path.exists():
            data = json.loads(data_path.read_text(encoding="utf-8"))
            store = {
                "users": list(data.get("users", [])),
                "pantries": list(data.get("pantries", [])),
                "shifts": list(data.get("shifts", [])),
            }
            if store["shifts"]:
                next_shift_id = max(s.get("shift_id", 0) for s in store["shifts"]) + 1
            else:
                next_shift_id = 1
            return


load_seed_data()


@app.before_request
def set_current_user() -> None:
    """Allow switching user via ?user_id=X query parameter for testing."""
    user_id = request.args.get("user_id", type=int) or DEFAULT_USER_ID
    g.current_user_id = user_id


def find_pantry_by_id(pantry_id: int) -> dict[str, Any] | None:
    return next((p for p in store["pantries"] if p.get("id") == pantry_id), None)


def find_pantry_by_slug(slug: str) -> dict[str, Any] | None:
    return next((p for p in store["pantries"] if p.get("slug") == slug), None)


def current_user() -> dict[str, Any] | None:
    user_id = getattr(g, "current_user_id", DEFAULT_USER_ID)
    return next((u for u in store["users"] if u.get("id") == user_id), None)


def pantries_for_current_user() -> list[dict[str, Any]]:
    """Pantries the current user can manage: all for SUPER_ADMIN, else where lead_id = current user."""
    user = current_user()
    if not user:
        return []
    user_id = getattr(g, "current_user_id", DEFAULT_USER_ID)
    role = user.get("role", "")
    if role == "SUPER_ADMIN":
        return list(store["pantries"])
    if role == "PANTRY_LEAD":
        return [p for p in store["pantries"] if p.get("lead_id") == user_id]
    return []


# ---------- API routes (all under /api) ----------


@app.get("/api/me")
def get_current_user() -> Any:
    user = current_user()
    if user is None:
        user = {"id": 1, "email": "lead@example.org", "role": "PANTRY_LEAD"}
    return jsonify(user)


@app.get("/api/users")
def list_users() -> Any:
    """List users (SUPER_ADMIN only). Optional role filter: /api/users?role=PANTRY_LEAD."""
    user = current_user()
    if not user or user.get("role") != "SUPER_ADMIN":
        return jsonify({"error": "Forbidden"}), 403

    role = request.args.get("role")
    users = list(store["users"])
    if role:
        users = [u for u in users if u.get("role") == role]
    return jsonify(users)


@app.get("/api/pantries")
def list_pantries() -> Any:
    pantries = pantries_for_current_user()
    return jsonify(pantries)


@app.get("/api/pantries/<int:pantry_id>")
def get_pantry(pantry_id: int) -> Any:
    pantry = find_pantry_by_id(pantry_id)
    if pantry is None:
        return jsonify({"error": "Pantry not found"}), 404
    allowed = {p.get("id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(pantry)


@app.get("/api/pantries/slug/<slug>")
def get_pantry_by_slug(slug: str) -> Any:
    pantry = find_pantry_by_slug(slug)
    if pantry is None:
        return jsonify({"error": "Pantry not found"}), 404
    return jsonify(pantry)


@app.patch("/api/pantries/<int:pantry_id>")
def update_pantry(pantry_id: int) -> Any:
    """SUPER_ADMIN-only partial update. Currently supports changing lead_id."""
    user = current_user()
    if not user or user.get("role") != "SUPER_ADMIN":
        return jsonify({"error": "Forbidden"}), 403

    pantry = find_pantry_by_id(pantry_id)
    if pantry is None:
        return jsonify({"error": "Pantry not found"}), 404

    payload = request.get_json(silent=True) or {}
    if "lead_id" in payload:
        lead_id = payload["lead_id"]
        if lead_id is not None:
            # Validate that lead exists and has PANTRY_LEAD role
            lead = next(
                (
                    u
                    for u in store["users"]
                    if u.get("id") == lead_id and u.get("role") == "PANTRY_LEAD"
                ),
                None,
            )
            if lead is None:
                return jsonify({"error": "Invalid lead_id"}), 400
        pantry["lead_id"] = lead_id

    return jsonify(pantry)


@app.get("/api/pantries/<int:pantry_id>/shifts")
def get_shifts(pantry_id: int) -> Any:
    allowed = {p.get("id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    shifts = [s for s in store["shifts"] if s.get("pantry_id") == pantry_id]
    return jsonify(shifts)


@app.post("/api/pantries/<int:pantry_id>/shifts")
def create_shift(pantry_id: int) -> Any:
    global next_shift_id
    allowed = {p.get("id") for p in pantries_for_current_user()}
    if pantry_id not in allowed:
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    required = ["role_name", "start_time", "end_time", "required_count"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        required_count = int(payload["required_count"])
    except (TypeError, ValueError):
        return jsonify({"error": "required_count must be an integer"}), 400

    if required_count < 1:
        return jsonify({"error": "required_count must be at least 1"}), 400

    shift = {
        "shift_id": next_shift_id,
        "pantry_id": pantry_id,
        "role_name": payload["role_name"],
        "start_time": payload["start_time"],
        "end_time": payload["end_time"],
        "filled_count": 0,
        "required_count": required_count,
        "status": "Open",
    }
    next_shift_id += 1
    store["shifts"].append(shift)

    response = {
        "shift_id": shift["shift_id"],
        "role_name": shift["role_name"],
        "filled_count": shift["filled_count"],
        "required_count": shift["required_count"],
        "status": shift["status"],
    }
    return jsonify(response), 201


@app.get("/api/public/pantries/<slug>/shifts")
def get_public_shifts(slug: str) -> Any:
    pantry = find_pantry_by_slug(slug)
    if pantry is None:
        return jsonify([])
    pantry_id = pantry.get("id")
    shifts = [s for s in store["shifts"] if s.get("pantry_id") == pantry_id]
    return jsonify(shifts)


@app.get("/")
def index() -> Any:
    """Redirect to lead dashboard by default."""
    return redirect(url_for("lead_dashboard"))


@app.get("/lead")
def lead_dashboard() -> Any:
    """Pantry lead dashboard + calendar UI."""
    return render_template("lead.html")


@app.get("/admin/assign")
def admin_assign() -> Any:
    """Super admin UI for assigning pantries to leads."""
    return render_template("admin_assign.html")


@app.get("/pantries/<slug>/shifts")
def public_shifts_page(slug: str) -> Any:
    """Public shifts page for a pantry slug."""
    pantry = find_pantry_by_slug(slug)
    if pantry is None:
        # Keep it simple: 404 JSON for now
        return jsonify({"error": "Pantry not found"}), 404
    return render_template("public_shifts.html", slug=slug, pantry_name=pantry.get("name", "Pantry"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
