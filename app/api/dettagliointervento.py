from flask import Blueprint, jsonify, request

from .mock_interventi_store import apply_intervento_action, get_intervento_detail

bp = Blueprint("dettagliointervento", __name__)


@bp.get("/<string:request_id>")
def get_detail(request_id):
    detail = get_intervento_detail(request_id)
    if detail is None:
        return jsonify({
            "error": "NOT_FOUND",
            "message": "Intervento non trovato",
        }), 404

    return jsonify({"data": detail}), 200


def _handle_action(request_id, action):
    request.get_json(silent=True) or {}

    response, error = apply_intervento_action(request_id, action)
    if error is not None:
        return jsonify({
            "error": error["error"],
            "message": error["message"],
        }), error["status_code"]

    return jsonify(response), 200


@bp.post("/<string:request_id>/take-in-charge")
def take_in_charge(request_id):
    return _handle_action(request_id, "take_in_charge")


@bp.post("/<string:request_id>/reject")
def reject(request_id):
    return _handle_action(request_id, "reject")


@bp.post("/<string:request_id>/complete")
def complete(request_id):
    return _handle_action(request_id, "complete")
