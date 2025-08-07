from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class LeaderboardEntry(db.Model):
    __tablename__ = 'leaderboard_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    promotore_id = db.Column(db.Integer, db.ForeignKey('promotore.id'), nullable=False)
    mese = db.Column(db.Integer, nullable=False)  # 1-12
    anno = db.Column(db.Integer, nullable=False)  # 2025, 2026, etc.
    
    # Metriche per il calcolo del punteggio
    collaborazioni_completate = db.Column(db.Integer, default=0)
    richieste_inviate = db.Column(db.Integer, default=0)
    richieste_accettate = db.Column(db.Integer, default=0)
    rating_medio = db.Column(db.Float, default=0.0)  # 0-5
    giorni_attivo = db.Column(db.Integer, default=0)  # giorni di attività nel mese
    
    # Punteggio calcolato
    punteggio_totale = db.Column(db.Float, default=0.0)
    posizione = db.Column(db.Integer, default=0)  # posizione in classifica
    
    # Timestamp
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_aggiornamento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    promotore = db.relationship('Promotore', backref='leaderboard_entries')
    
    def __repr__(self):
        return f'<LeaderboardEntry {self.promotore_id} - {self.mese}/{self.anno}: {self.punteggio_totale}>'
    
    def calcola_punteggio(self):
        """
        Calcola il punteggio totale basato sulle metriche
        Formula: (collaborazioni * 100) + (tasso_accettazione * 50) + (rating * 20) + (giorni_attivo * 2)
        """
        # Tasso di accettazione (0-1)
        tasso_accettazione = 0
        if self.richieste_inviate > 0:
            tasso_accettazione = self.richieste_accettate / self.richieste_inviate
        
        # Calcolo punteggio
        punteggio = (
            (self.collaborazioni_completate * 100) +  # 100 punti per collaborazione
            (tasso_accettazione * 50) +              # fino a 50 punti per tasso accettazione
            (self.rating_medio * 20) +               # fino a 100 punti per rating (5*20)
            (self.giorni_attivo * 2)                 # 2 punti per giorno attivo
        )
        
        self.punteggio_totale = round(punteggio, 2)
        return self.punteggio_totale
    
    def to_dict(self):
        """Converte l'entry in dizionario per JSON"""
        return {
            'id': self.id,
            'promotore_id': self.promotore_id,
            'mese': self.mese,
            'anno': self.anno,
            'collaborazioni_completate': self.collaborazioni_completate,
            'richieste_inviate': self.richieste_inviate,
            'richieste_accettate': self.richieste_accettate,
            'rating_medio': self.rating_medio,
            'giorni_attivo': self.giorni_attivo,
            'punteggio_totale': self.punteggio_totale,
            'posizione': self.posizione,
            'data_creazione': self.data_creazione.isoformat() if self.data_creazione else None,
            'data_aggiornamento': self.data_aggiornamento.isoformat() if self.data_aggiornamento else None,
            # Dati del promotore
            'promotore_email': self.promotore.user.email if self.promotore and self.promotore.user else None,
            'promotore_industry': self.promotore.industry if self.promotore else None
        }
    
    @staticmethod
    def get_current_month_year():
        """Restituisce mese e anno correnti"""
        now = datetime.utcnow()
        return now.month, now.year
    
    @staticmethod
    def get_or_create_entry(promotore_id, mese=None, anno=None):
        """Ottiene o crea un'entry per il promotore nel mese/anno specificato"""
        if mese is None or anno is None:
            mese, anno = LeaderboardEntry.get_current_month_year()
        
        entry = LeaderboardEntry.query.filter_by(
            promotore_id=promotore_id,
            mese=mese,
            anno=anno
        ).first()
        
        if not entry:
            entry = LeaderboardEntry(
                promotore_id=promotore_id,
                mese=mese,
                anno=anno
            )
            db.session.add(entry)
            db.session.commit()
        
        return entry

