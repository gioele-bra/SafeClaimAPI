from flask import Blueprint, jsonify

bp = Blueprint("common", __name__)

# TODO: Endpoint comuni di supporto.
# L'emissione token è delegata a Keycloak.


@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
