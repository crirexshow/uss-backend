from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum
from src.models.user import db

class PerkType(Enum):
    PRIORITY_LISTING = "priority_listing"
    FEATURED_PROFILE = "featured_profile"
    BOOST_VISIBILITY = "boost_visibility"
    PREMIUM_BADGE = "premium_badge"

class TransactionType(Enum):
    PURCHASE = "purchase"
    SPEND = "spend"
    REFUND = "refund"
    BONUS = "bonus"

class PerkPointsBalance(db.Model):
    __tablename__ = 'perk_points_balance'
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, nullable=False)
    total_points = db.Column(db.Integer, nullable=False, default=0)
    available_points = db.Column(db.Integer, nullable=False, default=0)
    spent_points = db.Column(db.Integer, nullable=False, default=0)
    
    # Metadati
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, azienda_id):
        self.azienda_id = azienda_id
        self.total_points = 0
        self.available_points = 0
        self.spent_points = 0
    
    def add_points(self, points, transaction_type=TransactionType.PURCHASE):
        """Aggiunge punti al saldo"""
        self.total_points += points
        self.available_points += points
        self.updated_at = datetime.utcnow()
        
        # Crea transazione
        transaction = PerkPointsTransaction(
            azienda_id=self.azienda_id,
            points=points,
            transaction_type=transaction_type,
            balance_after=self.available_points
        )
        db.session.add(transaction)
        
        return transaction
    
    def spend_points(self, points, perk_type, description=""):
        """Spende punti per un perk"""
        if self.available_points < points:
            return False, "Punti insufficienti"
        
        self.available_points -= points
        self.spent_points += points
        self.updated_at = datetime.utcnow()
        
        # Crea transazione
        transaction = PerkPointsTransaction(
            azienda_id=self.azienda_id,
            points=-points,
            transaction_type=TransactionType.SPEND,
            balance_after=self.available_points,
            perk_type=perk_type,
            description=description
        )
        db.session.add(transaction)
        
        return True, transaction
    
    def can_afford(self, points):
        """Verifica se l'azienda può permettersi di spendere i punti"""
        return self.available_points >= points
    
    def to_dict(self):
        return {
            'id': self.id,
            'azienda_id': self.azienda_id,
            'total_points': self.total_points,
            'available_points': self.available_points,
            'spent_points': self.spent_points,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class PerkPointsTransaction(db.Model):
    __tablename__ = 'perk_points_transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Positivo per acquisti, negativo per spese
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    balance_after = db.Column(db.Integer, nullable=False)
    
    # Dettagli perk (se applicabile)
    perk_type = db.Column(db.Enum(PerkType), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    
    # Metadati
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'azienda_id': self.azienda_id,
            'points': self.points,
            'transaction_type': self.transaction_type.value,
            'balance_after': self.balance_after,
            'perk_type': self.perk_type.value if self.perk_type else None,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

class ActivePerk(db.Model):
    __tablename__ = 'active_perk'
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, nullable=False)
    perk_type = db.Column(db.Enum(PerkType), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    
    # Durata e scadenza
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Metadati
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __init__(self, azienda_id, perk_type, points_spent, duration_days=30):
        self.azienda_id = azienda_id
        self.perk_type = perk_type
        self.points_spent = points_spent
        self.start_date = datetime.utcnow()
        self.end_date = self.start_date + timedelta(days=duration_days)
        self.is_active = True
    
    def is_expired(self):
        """Verifica se il perk è scaduto"""
        return datetime.utcnow() > self.end_date
    
    def deactivate(self):
        """Disattiva il perk"""
        self.is_active = False
    
    def get_remaining_days(self):
        """Restituisce i giorni rimanenti"""
        if self.is_expired():
            return 0
        return (self.end_date - datetime.utcnow()).days
    
    def to_dict(self):
        return {
            'id': self.id,
            'azienda_id': self.azienda_id,
            'perk_type': self.perk_type.value,
            'points_spent': self.points_spent,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'is_active': self.is_active,
            'is_expired': self.is_expired(),
            'remaining_days': self.get_remaining_days(),
            'created_at': self.created_at.isoformat()
        }

class PerkPackage(db.Model):
    __tablename__ = 'perk_package'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    perk_type = db.Column(db.Enum(PerkType), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Metadati
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_default_packages():
        """Restituisce i pacchetti perk di default"""
        return [
            {
                'name': 'Listing Prioritario',
                'description': 'Il tuo profilo appare in cima ai risultati di ricerca per 30 giorni',
                'perk_type': PerkType.PRIORITY_LISTING,
                'points_cost': 100,
                'duration_days': 30
            },
            {
                'name': 'Profilo in Evidenza',
                'description': 'Il tuo profilo viene evidenziato con un badge speciale per 30 giorni',
                'perk_type': PerkType.FEATURED_PROFILE,
                'points_cost': 150,
                'duration_days': 30
            },
            {
                'name': 'Boost Visibilità',
                'description': 'Aumenta la visibilità del tuo profilo del 300% per 7 giorni',
                'perk_type': PerkType.BOOST_VISIBILITY,
                'points_cost': 75,
                'duration_days': 7
            },
            {
                'name': 'Badge Premium',
                'description': 'Mostra un badge premium sul tuo profilo per 60 giorni',
                'perk_type': PerkType.PREMIUM_BADGE,
                'points_cost': 200,
                'duration_days': 60
            }
        ]
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'perk_type': self.perk_type.value,
            'points_cost': self.points_cost,
            'duration_days': self.duration_days,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Funzioni di utilità per il sistema Perk Points
def get_points_pricing():
    """Restituisce i prezzi per l'acquisto di punti"""
    return [
        {'points': 100, 'price': 9.99, 'bonus': 0, 'popular': False},
        {'points': 250, 'price': 19.99, 'bonus': 25, 'popular': True},
        {'points': 500, 'price': 34.99, 'bonus': 75, 'popular': False},
        {'points': 1000, 'price': 59.99, 'bonus': 200, 'popular': False},
    ]

def calculate_perk_priority_score(azienda_id):
    """Calcola il punteggio di priorità basato sui perk attivi"""
    active_perks = ActivePerk.query.filter_by(
        azienda_id=azienda_id, 
        is_active=True
    ).filter(ActivePerk.end_date > datetime.utcnow()).all()
    
    priority_score = 0
    
    for perk in active_perks:
        if perk.perk_type == PerkType.PRIORITY_LISTING:
            priority_score += 1000
        elif perk.perk_type == PerkType.FEATURED_PROFILE:
            priority_score += 500
        elif perk.perk_type == PerkType.BOOST_VISIBILITY:
            priority_score += 300
        elif perk.perk_type == PerkType.PREMIUM_BADGE:
            priority_score += 100
    
    return priority_score

def cleanup_expired_perks():
    """Pulisce i perk scaduti (da chiamare periodicamente)"""
    expired_perks = ActivePerk.query.filter(
        ActivePerk.is_active == True,
        ActivePerk.end_date < datetime.utcnow()
    ).all()
    
    for perk in expired_perks:
        perk.deactivate()
    
    db.session.commit()
    return len(expired_perks)

