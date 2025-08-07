from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum

db = SQLAlchemy()

class PlanType(Enum):
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

class Subscription(db.Model):
    __tablename__ = 'subscription'
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, nullable=False)
    plan_type = db.Column(db.Enum(PlanType), nullable=False, default=PlanType.BASIC)
    status = db.Column(db.Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Date e periodo
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    next_billing_date = db.Column(db.DateTime, nullable=True)
    
    # Pricing
    monthly_price = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(3), nullable=False, default='EUR')
    
    # Limitazioni e utilizzo
    monthly_requests_limit = db.Column(db.Integer, nullable=False, default=5)
    monthly_requests_used = db.Column(db.Integer, nullable=False, default=0)
    last_reset_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Metadati
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    # azienda = db.relationship('User', backref='subscription', uselist=False)
    
    def __init__(self, azienda_id, plan_type=PlanType.BASIC):
        self.azienda_id = azienda_id
        self.plan_type = plan_type
        self.set_plan_limits()
        
        if plan_type != PlanType.BASIC:
            self.next_billing_date = datetime.utcnow() + timedelta(days=30)
            self.end_date = self.next_billing_date
    
    def set_plan_limits(self):
        """Imposta i limiti e prezzi basati sul tipo di piano"""
        plan_configs = {
            PlanType.BASIC: {
                'monthly_price': 0.0,
                'monthly_requests_limit': 5,
            },
            PlanType.PRO: {
                'monthly_price': 29.0,
                'monthly_requests_limit': 50,
            },
            PlanType.PREMIUM: {
                'monthly_price': 99.0,
                'monthly_requests_limit': -1,  # Illimitato
            }
        }
        
        config = plan_configs.get(self.plan_type, plan_configs[PlanType.BASIC])
        self.monthly_price = config['monthly_price']
        self.monthly_requests_limit = config['monthly_requests_limit']
    
    def can_make_request(self):
        """Verifica se l'azienda può fare una nuova richiesta"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        # Reset mensile del contatore
        if self.should_reset_monthly_usage():
            self.reset_monthly_usage()
        
        # Piano Premium ha richieste illimitate
        if self.monthly_requests_limit == -1:
            return True
        
        return self.monthly_requests_used < self.monthly_requests_limit
    
    def use_request(self):
        """Incrementa il contatore delle richieste utilizzate"""
        if self.can_make_request():
            self.monthly_requests_used += 1
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def should_reset_monthly_usage(self):
        """Verifica se è necessario resettare l'utilizzo mensile"""
        now = datetime.utcnow()
        return (now - self.last_reset_date).days >= 30
    
    def reset_monthly_usage(self):
        """Resetta il contatore mensile delle richieste"""
        self.monthly_requests_used = 0
        self.last_reset_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def is_expired(self):
        """Verifica se l'abbonamento è scaduto"""
        if self.plan_type == PlanType.BASIC:
            return False
        
        if self.end_date and datetime.utcnow() > self.end_date:
            return True
        
        return False
    
    def get_remaining_requests(self):
        """Restituisce il numero di richieste rimanenti"""
        if self.monthly_requests_limit == -1:
            return -1  # Illimitato
        
        return max(0, self.monthly_requests_limit - self.monthly_requests_used)
    
    def get_plan_features(self):
        """Restituisce le funzionalità del piano corrente"""
        features = {
            PlanType.BASIC: {
                'name': 'Basic',
                'price': '€0/mese',
                'requests_limit': '5 richieste/mese',
                'search_filters': 'Limitati',
                'analytics': False,
                'priority_support': False,
                'featured_listing': False,
            },
            PlanType.PRO: {
                'name': 'Pro',
                'price': '€29/mese',
                'requests_limit': '50 richieste/mese',
                'search_filters': 'Avanzati',
                'analytics': True,
                'priority_support': False,
                'featured_listing': False,
            },
            PlanType.PREMIUM: {
                'name': 'Premium',
                'price': '€99/mese',
                'requests_limit': 'Illimitate',
                'search_filters': 'Completi',
                'analytics': True,
                'priority_support': True,
                'featured_listing': True,
            }
        }
        
        return features.get(self.plan_type, features[PlanType.BASIC])
    
    def upgrade_plan(self, new_plan_type):
        """Aggiorna il piano di abbonamento"""
        if new_plan_type == self.plan_type:
            return False
        
        old_plan = self.plan_type
        self.plan_type = new_plan_type
        self.set_plan_limits()
        
        # Aggiorna le date di fatturazione per piani a pagamento
        if new_plan_type != PlanType.BASIC:
            if old_plan == PlanType.BASIC:
                # Primo upgrade da Basic
                self.start_date = datetime.utcnow()
                self.next_billing_date = datetime.utcnow() + timedelta(days=30)
                self.end_date = self.next_billing_date
            else:
                # Cambio tra piani a pagamento - mantieni la data di scadenza
                pass
        else:
            # Downgrade a Basic
            self.next_billing_date = None
            self.end_date = None
        
        self.status = SubscriptionStatus.ACTIVE
        self.updated_at = datetime.utcnow()
        return True
    
    def cancel_subscription(self):
        """Cancella l'abbonamento"""
        self.status = SubscriptionStatus.CANCELLED
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Converte l'oggetto in dizionario per JSON"""
        return {
            'id': self.id,
            'azienda_id': self.azienda_id,
            'plan_type': self.plan_type.value,
            'status': self.status.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'monthly_price': self.monthly_price,
            'currency': self.currency,
            'monthly_requests_limit': self.monthly_requests_limit,
            'monthly_requests_used': self.monthly_requests_used,
            'remaining_requests': self.get_remaining_requests(),
            'features': self.get_plan_features(),
            'is_expired': self.is_expired(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

