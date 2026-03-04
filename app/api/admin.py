from flask import Blueprint, jsonify, request

bp = Blueprint("claims", __name__)

# finta "DB" in memoria (solo demo)
CLAIMS = [
    {"id": 1, "title": "Sinistro 001", "status": "open"},
    {"id": 2, "title": "Sinistro 002", "status": "closed"},
]

@bp.get("/")
def list_claims():
    status = request.args.get("status")
    if status:
        return jsonify([c for c in CLAIMS if c["status"] == status])
    return jsonify(CLAIMS)

@bp.get("/<int:claim_id>")
def get_claim(claim_id: int):
    claim = next((c for c in CLAIMS if c["id"] == claim_id), None)
    if not claim:
        return jsonify({"error": "NOT_FOUND", "message": "Claim non trovato"}), 404
    return jsonify(claim)

@bp.post("/")
def create_claim():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "BAD_REQUEST", "message": "title obbligatorio"}), 400

    new_id = max(c["id"] for c in CLAIMS) + 1 if CLAIMS else 1
    claim = {"id": new_id, "title": title, "status": "open"}
    CLAIMS.append(claim)
    return jsonify(claim), 201