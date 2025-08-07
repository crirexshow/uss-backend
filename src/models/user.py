from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    tipo_utente = db.Column(db.String(20), nullable=False)  # 'Promotore' o 'Azienda'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'tipo_utente': self.tipo_utente,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Promotore(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    industry = db.Column(db.String(30), nullable=False)  # Beauty, Food & Restaurant, Fashion, Travel, Tech, Other
    instagram_link = db.Column(db.String(255), nullable=True)
    tiktok_link = db.Column(db.String(255), nullable=True)
    linkedin_link = db.Column(db.String(255), nullable=True)
    insight_screenshot_path = db.Column(db.String(255), nullable=True)
    foto_visualizzazioni_1_path = db.Column(db.String(255), nullable=True)
    foto_visualizzazioni_2_path = db.Column(db.String(255), nullable=True)
    foto_visualizzazioni_3_path = db.Column(db.String(255), nullable=True)
    ultimo_aggiornamento_insight = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('promotore', uselist=False))

    def __repr__(self):
        return f'<Promotore {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'industry': self.industry,
            'instagram_link': self.instagram_link,
            'tiktok_link': self.tiktok_link,
            'linkedin_link': self.linkedin_link,
            'insight_screenshot_path': self.insight_screenshot_path,
            'foto_visualizzazioni_1_path': self.foto_visualizzazioni_1_path,
            'foto_visualizzazioni_2_path': self.foto_visualizzazioni_2_path,
            'foto_visualizzazioni_3_path': self.foto_visualizzazioni_3_path,
            'ultimo_aggiornamento_insight': self.ultimo_aggiornamento_insight.isoformat() if self.ultimo_aggiornamento_insight else None
        }

class Azienda(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nome_attivita = db.Column(db.String(255), nullable=False)
    tipo_attivita = db.Column(db.String(255), nullable=False)
    min_visualizzazioni_richieste = db.Column(db.Integer, nullable=True)
    localita = db.Column(db.String(255), nullable=False)
    
    user = db.relationship('User', backref=db.backref('azienda', uselist=False))

    def __repr__(self):
        return f'<Azienda {self.nome_attivita}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome_attivita': self.nome_attivita,
            'tipo_attivita': self.tipo_attivita,
            'min_visualizzazioni_richieste': self.min_visualizzazioni_richieste,
            'localita': self.localita
        }

class Richiesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    promotore_id = db.Column(db.Integer, db.ForeignKey('promotore.id'), nullable=False)
    azienda_id = db.Column(db.Integer, db.ForeignKey('azienda.id'), nullable=False)
    stato = db.Column(db.String(50), nullable=False, default='In sospeso')  # 'In sospeso', 'Accettata', 'Rifiutata', 'In negoziazione'
    messaggio_iniziale = db.Column(db.Text, nullable=False)  # Messaggio iniziale del promotore
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_aggiornamento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_accettazione = db.Column(db.DateTime, nullable=True)  # Quando la richiesta è stata accettata
    
    promotore = db.relationship('Promotore', backref='richieste_inviate')
    azienda = db.relationship('Azienda', backref='richieste_ricevute')

    def __repr__(self):
        return f'<Richiesta {self.id}>'

    def to_dict(self, include_sensitive_data=False):
        """
        Restituisce i dati della richiesta.
        include_sensitive_data: se True, include email e link social (solo se richiesta accettata)
        """
        result = {
            'id': self.id,
            'promotore_id': self.promotore_id,
            'azienda_id': self.azienda_id,
            'stato': self.stato,
            'messaggio_iniziale': self.messaggio_iniziale,
            'data_creazione': self.data_creazione.isoformat() if self.data_creazione else None,
            'data_aggiornamento': self.data_aggiornamento.isoformat() if self.data_aggiornamento else None,
            'data_accettazione': self.data_accettazione.isoformat() if self.data_accettazione else None
        }
        
        # Aggiungi dati del promotore
        if self.promotore and self.promotore.user:
            promotore_data = {
                'industry': self.promotore.industry,
                'email': '***@***.***' if not include_sensitive_data else self.promotore.user.email,
            }
            
            # Link social oscurati se la richiesta non è accettata
            if include_sensitive_data and self.stato == 'Accettata':
                promotore_data.update({
                    'instagram_link': self.promotore.instagram_link,
                    'tiktok_link': self.promotore.tiktok_link,
                    'linkedin_link': self.promotore.linkedin_link,
                })
            else:
                promotore_data.update({
                    'instagram_link': 'Disponibile dopo accettazione' if self.promotore.instagram_link else None,
                    'tiktok_link': 'Disponibile dopo accettazione' if self.promotore.tiktok_link else None,
                    'linkedin_link': 'Disponibile dopo accettazione' if self.promotore.linkedin_link else None,
                })
            
            result['promotore'] = promotore_data
        
        # Aggiungi dati dell'azienda
        if self.azienda and self.azienda.user:
            azienda_data = {
                'nome_attivita': self.azienda.nome_attivita,
                'tipo_attivita': self.azienda.tipo_attivita,
                'localita': self.azienda.localita,
                'min_visualizzazioni_richieste': self.azienda.min_visualizzazioni_richieste,
                'email': '***@***.***' if not include_sensitive_data else self.azienda.user.email,
            }
            result['azienda'] = azienda_data
        
        return result

