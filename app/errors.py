from flask import jsonify

def register_error_handlers(app):

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": getattr(e, "description", "Token non valido o assente"),
            "code": 401,
        }), 401

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "NOT_FOUND", "message": "Endpoint non trovato"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "METHOD_NOT_ALLOWED", "message": "Metodo non consentito"}), 405

    @app.errorhandler(500)
    def internal_error(_):
        return jsonify({"error": "INTERNAL_ERROR", "message": "Errore interno"}), 500