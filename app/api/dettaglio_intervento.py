from flask import Blueprint, jsonify

from .mock_interventi_store import get_request_detail, transition_request

bp = Blueprint("dettaglio_intervento", __name__)


@bp.get("/<request_id>")
def get_detail(request_id):
    detail = get_request_detail(request_id)
    if not detail:
        return jsonify({
            "error": "NOT_FOUND",
            "message": "Richiesta non trovata",
        }), 404

    return jsonify({"data": detail}), 200


@bp.post("/<request_id>/take-in-charge")
def take_in_charge(request_id):
    return _handle_transition(request_id, "take_in_charge")


@bp.post("/<request_id>/reject")
def reject(request_id):
    return _handle_transition(request_id, "reject")


@bp.post("/<request_id>/complete")
def complete(request_id):
    return _handle_transition(request_id, "complete")


def _handle_transition(request_id, action):
    result, error = transition_request(request_id, action)
    if error:
        code, message, status_code = error
        return jsonify({
            "error": code,
            "message": message,
        }), status_code

    return jsonify(result), 200
