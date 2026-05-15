"""Endpoint comuni di supporto (health-check)."""

from flask import Blueprint, jsonify

bp = Blueprint("common", __name__)


def health():
    return jsonify({"status": "ok"}), 200


# Registrazione su entrambi i path:
#   * `/api/v1/health` (canonical, registrato in __init__ con url_prefix="/api/v1")
#   * `/api/common/health` (legacy, registrato in __init__ con url_prefix="/api/common")
bp.add_url_rule("/health", "health", health, methods=["GET"])
