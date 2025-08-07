from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from src.models.user import db, User
from src.models.subscription import Subscription, PlanType, SubscriptionStatus
from datetime import datetime

subscription_bp = Blueprint('subscription', __name__)

def require_auth():
    """Decorator per richiedere autenticazione"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Non autenticato'}), 401
            
            user = User.query.get(session['user_id'])
            if not user:
                return jsonify({'error': 'Utente non trovato'}), 404
            
            return f(user, *args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

@subscription_bp.route('/current', methods=['GET'])
@cross_origin()
@require_auth()
def get_current_subscription(current_user):
    """Ottiene l'abbonamento corrente dell'azienda"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono avere abbonamenti'}), 403
        
        # Cerca l'abbonamento esistente
        subscription = Subscription.query.filter_by(azienda_id=current_user.id).first()
        
        if not subscription:
            # Crea abbonamento Basic di default
            subscription = Subscription(azienda_id=current_user.id, plan_type=PlanType.BASIC)
            db.session.add(subscription)
            db.session.commit()
        
        # Verifica se l'abbonamento è scaduto
        if subscription.is_expired():
            subscription.status = SubscriptionStatus.EXPIRED
            db.session.commit()
        
        return jsonify({
            'success': True,
            'subscription': subscription.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/plans', methods=['GET'])
@cross_origin()
def get_available_plans():
    """Ottiene tutti i piani disponibili"""
    try:
        plans = []
        
        for plan_type in PlanType:
            # Crea un oggetto temporaneo per ottenere le features
            temp_subscription = Subscription(azienda_id=0, plan_type=plan_type)
            features = temp_subscription.get_plan_features()
            
            plan_info = {
                'type': plan_type.value,
                'name': features['name'],
                'price': features['price'],
                'monthly_price': temp_subscription.monthly_price,
                'features': {
                    'requests_limit': features['requests_limit'],
                    'search_filters': features['search_filters'],
                    'analytics': features['analytics'],
                    'priority_support': features['priority_support'],
                    'featured_listing': features['featured_listing'],
                },
                'recommended': plan_type == PlanType.PRO  # Piano consigliato
            }
            plans.append(plan_info)
        
        return jsonify({
            'success': True,
            'plans': plans
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/upgrade', methods=['POST'])
@cross_origin()
@require_auth()
def upgrade_subscription(current_user):
    """Aggiorna il piano di abbonamento"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono aggiornare abbonamenti'}), 403
        
        data = request.get_json()
        new_plan_type_str = data.get('plan_type')
        
        if not new_plan_type_str:
            return jsonify({'error': 'Tipo di piano richiesto'}), 400
        
        try:
            new_plan_type = PlanType(new_plan_type_str)
        except ValueError:
            return jsonify({'error': 'Tipo di piano non valido'}), 400
        
        # Ottieni o crea l'abbonamento
        subscription = Subscription.query.filter_by(azienda_id=current_user.id).first()
        
        if not subscription:
            subscription = Subscription(azienda_id=current_user.id, plan_type=PlanType.BASIC)
            db.session.add(subscription)
        
        # Aggiorna il piano
        if subscription.upgrade_plan(new_plan_type):
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Piano aggiornato a {new_plan_type.value.title()}',
                'subscription': subscription.to_dict()
            })
        else:
            return jsonify({'error': 'Impossibile aggiornare al piano selezionato'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/cancel', methods=['POST'])
@cross_origin()
@require_auth()
def cancel_subscription(current_user):

    """Cancella l'abbonamento corrente"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono cancellare abbonamenti'}), 403
        
        subscription = Subscription.query.filter_by(azienda_id=current_user.id).first()
        
        if not subscription:
            return jsonify({'error': 'Nessun abbonamento trovato'}), 404
        
        if subscription.plan_type == PlanType.BASIC:
            return jsonify({'error': 'Il piano Basic non può essere cancellato'}), 400
        
        subscription.cancel_subscription()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Abbonamento cancellato con successo',
            'subscription': subscription.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/usage', methods=['GET'])
@cross_origin()
@require_auth()
def get_usage_stats(current_user):
    """Ottiene le statistiche di utilizzo dell'abbonamento"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono visualizzare statistiche'}), 403
        
        subscription = Subscription.query.filter_by(azienda_id=current_user.id).first()
        
        if not subscription:
            return jsonify({'error': 'Nessun abbonamento trovato'}), 404
        
        # Calcola giorni rimanenti nel ciclo corrente
        days_until_reset = 30 - (datetime.utcnow() - subscription.last_reset_date).days
        
        usage_stats = {
            'current_plan': subscription.get_plan_features(),
            'requests_used': subscription.monthly_requests_used,
            'requests_limit': subscription.monthly_requests_limit,
            'requests_remaining': subscription.get_remaining_requests(),
            'days_until_reset': max(0, days_until_reset),
            'usage_percentage': (
                (subscription.monthly_requests_used / subscription.monthly_requests_limit * 100)
                if subscription.monthly_requests_limit > 0 else 0
            ),
            'can_make_request': subscription.can_make_request(),
            'next_billing_date': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            'is_expired': subscription.is_expired()
        }
        
        return jsonify({
            'success': True,
            'usage': usage_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/check-limits', methods=['POST'])
@cross_origin()
@require_auth()
def check_request_limits(current_user):

    """Verifica e consuma una richiesta se possibile"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende hanno limiti di richieste'}), 403
        
        subscription = Subscription.query.filter_by(azienda_id=current_user.id).first()
        
        if not subscription:
            # Crea abbonamento Basic di default
            subscription = Subscription(azienda_id=current_user.id, plan_type=PlanType.BASIC)
            db.session.add(subscription)
        
        if subscription.use_request():
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Richiesta autorizzata',
                'remaining_requests': subscription.get_remaining_requests()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Limite di richieste raggiunto per il piano corrente',
                'current_plan': subscription.get_plan_features()['name'],
                'upgrade_required': True
            }), 429  # Too Many Requests
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/billing-history', methods=['GET'])
@cross_origin()
@require_auth()
def get_billing_history(current_user):
    """Ottiene la cronologia di fatturazione (placeholder)"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono visualizzare fatturazione'}), 403
        
        # Placeholder per cronologia fatturazione
        # In un'implementazione reale, questo si collegherebbe a un sistema di pagamento
        billing_history = [
            {
                'id': 1,
                'date': '2024-01-15',
                'amount': 29.00,
                'currency': 'EUR',
                'plan': 'Pro',
                'status': 'paid',
                'invoice_url': '#'
            }
        ]
        
        return jsonify({
            'success': True,
            'billing_history': billing_history
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

