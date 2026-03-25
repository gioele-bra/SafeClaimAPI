from datetime import datetime
from sqlalchemy.dialects.mysql import SET

class User(db.Model):
    __tablename__ = 'utenti'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cognome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    telefono = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    ruolo = db.Column(SET(['admin', 'user', 'moderator']), nullable=False)
    data_registrazione = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cognome': self.cognome,
            'email': self.email,
            'telefono': self.telefono,
            'ruolo': list(self.ruolo) if self.ruolo else [],
            'data_registrazione': self.data_registrazione.isoformat()
        }