from flask import Blueprint, jsonify, request
from ..services.token_service import issue_token

bp = Blueprint("auth", __name__)

@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "BAD_REQUEST", "message": "username obbligatorio"}), 400

    token = issue_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"})