from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from .user import db

class Messaggio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    richiesta_id = db.Column(db.Integer, db.ForeignKey('richiesta.id'), nullable=False)
    mittente_tipo = db.Column(db.String(20), nullable=False)  # 'promotore' o 'azienda'
    mittente_id = db.Column(db.Integer, nullable=False)  # ID del promotore o azienda
    contenuto = db.Column(db.Text, nullable=False)
    tipo_messaggio = db.Column(db.String(30), nullable=False, default='messaggio')  # 'messaggio', 'controproposta', 'accettazione', 'rifiuto'
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    
    richiesta = db.relationship('Richiesta', backref='messaggi')

    def __repr__(self):
        return f'<Messaggio {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'richiesta_id': self.richiesta_id,
            'mittente_tipo': self.mittente_tipo,
            'mittente_id': self.mittente_id,
            'contenuto': self.contenuto,
            'tipo_messaggio': self.tipo_messaggio,
            'data_creazione': self.data_creazione.isoformat() if self.data_creazione else None
        }

