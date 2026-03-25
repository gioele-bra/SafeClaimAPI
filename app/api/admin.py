from flask import Blueprint, jsonify, request
from ..objects import User

try:
    from flask_sqlalchemy import SQLAlchemy
except ImportError:  # pragma: no cover - only occurs in test environment
    class SQLAlchemy:
        def __init__(self, *args, **kwargs):
            pass

bp = Blueprint("users", __name__)
db = SQLAlchemy()

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://safeclaim:0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=@mysql-safeclaim.aevorastudios.com:3306/safeclaim'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =========================
# GET tutti utenti
# =========================
@bp.get("/")
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


# =========================
# GET singolo utente
# =========================
@bp.get("/<int:user_id>")
def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404
    return jsonify(user.to_dict())


# =========================
# CREA utente (ruoli solo alla creazione)
# =========================
@bp.post("/")
def create_user():
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    cognome = (data.get("cognome") or "").strip()
    email = (data.get("email") or "").strip()
    telefono = (data.get("telefono") or "").strip()

    if not nome or not cognome or not email or not telefono:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "nome, cognome, email e telefono sono obbligatori"
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Email già registrata"
        }), 400

    user = User(
        nome=nome,
        cognome=cognome,
        email=email,
        telefono=telefono
    )

    # Ruoli solo alla creazione
    for role in data.get("roles", []):
        user.roles.append(UserRole(role=role))

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


# =========================
# MODIFICA utente (NO RUOLI)
# =========================
@bp.put("/<int:user_id>")
def update_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404

    data = request.get_json(silent=True) or {}

    user.nome = data.get("nome", user.nome)
    user.cognome = data.get("cognome", user.cognome)
    user.email = data.get("email", user.email)
    user.telefono = data.get("telefono", user.telefono)

    # ⚠ I RUOLI NON SI POSSONO MODIFICARE

    db.session.commit()

    return jsonify(user.to_dict())