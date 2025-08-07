from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
from src.models.user import db, User
from src.models.perk_points import (
    PerkPointsBalance, PerkPointsTransaction, ActivePerk, PerkPackage,
    PerkType, TransactionType, get_points_pricing, calculate_perk_priority_score,
    cleanup_expired_perks
)
from datetime import datetime

perk_points_bp = Blueprint('perk_points', __name__)

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

@perk_points_bp.route('/balance', methods=['GET'])
@cross_origin()
@require_auth()
def get_points_balance(current_user):
    """Ottiene il saldo punti dell'azienda"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono avere punti perk'}), 403
        
        # Ottieni o crea il saldo punti
        balance = PerkPointsBalance.query.filter_by(azienda_id=current_user.id).first()
        
        if not balance:
            balance = PerkPointsBalance(azienda_id=current_user.id)
            db.session.add(balance)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'balance': balance.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/pricing', methods=['GET'])
@cross_origin()
def get_points_pricing_info():
    """Ottiene i prezzi per l'acquisto di punti"""
    try:
        pricing = get_points_pricing()
        
        return jsonify({
            'success': True,
            'pricing': pricing
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/purchase', methods=['POST'])
@cross_origin()
@require_auth()
def purchase_points(current_user):
    """Acquista punti perk"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono acquistare punti perk'}), 403
        
        data = request.get_json()
        points_package = data.get('points_package')
        
        if not points_package:
            return jsonify({'error': 'Pacchetto punti richiesto'}), 400
        
        # Verifica che il pacchetto esista
        pricing = get_points_pricing()
        selected_package = None
        
        for package in pricing:
            if package['points'] == points_package:
                selected_package = package
                break
        
        if not selected_package:
            return jsonify({'error': 'Pacchetto punti non valido'}), 400
        
        # Ottieni o crea il saldo punti
        balance = PerkPointsBalance.query.filter_by(azienda_id=current_user.id).first()
        
        if not balance:
            balance = PerkPointsBalance(azienda_id=current_user.id)
            db.session.add(balance)
        
        # Calcola punti totali (base + bonus)
        total_points = selected_package['points'] + selected_package['bonus']
        
        # Aggiungi punti al saldo
        transaction = balance.add_points(total_points, TransactionType.PURCHASE)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Acquistati {total_points} punti con successo!',
            'transaction': transaction.to_dict(),
            'new_balance': balance.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/packages', methods=['GET'])
@cross_origin()
def get_perk_packages():
    """Ottiene tutti i pacchetti perk disponibili"""
    try:
        # Pulisci i perk scaduti
        cleanup_expired_perks()
        
        packages = PerkPackage.query.filter_by(is_active=True).all()
        
        # Se non ci sono pacchetti nel database, crea quelli di default
        if not packages:
            default_packages = PerkPackage.get_default_packages()
            
            for pkg_data in default_packages:
                package = PerkPackage(
                    name=pkg_data['name'],
                    description=pkg_data['description'],
                    perk_type=pkg_data['perk_type'],
                    points_cost=pkg_data['points_cost'],
                    duration_days=pkg_data['duration_days']
                )
                db.session.add(package)
            
            db.session.commit()
            packages = PerkPackage.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'packages': [pkg.to_dict() for pkg in packages]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/activate', methods=['POST'])
@cross_origin()
@require_auth()
def activate_perk(current_user):
    """Attiva un perk spendendo punti"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono attivare perk'}), 403
        
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return jsonify({'error': 'ID pacchetto richiesto'}), 400
        
        # Trova il pacchetto
        package = PerkPackage.query.get(package_id)
        
        if not package or not package.is_active:
            return jsonify({'error': 'Pacchetto non trovato o non disponibile'}), 404
        
        # Ottieni il saldo punti
        balance = PerkPointsBalance.query.filter_by(azienda_id=current_user.id).first()
        
        if not balance:
            return jsonify({'error': 'Saldo punti non trovato'}), 404
        
        # Verifica se l'azienda può permettersi il perk
        if not balance.can_afford(package.points_cost):
            return jsonify({
                'error': 'Punti insufficienti',
                'required': package.points_cost,
                'available': balance.available_points
            }), 400
        
        # Verifica se esiste già un perk attivo dello stesso tipo
        existing_perk = ActivePerk.query.filter_by(
            azienda_id=current_user.id,
            perk_type=package.perk_type,
            is_active=True
        ).filter(ActivePerk.end_date > datetime.utcnow()).first()
        
        if existing_perk:
            return jsonify({
                'error': f'Hai già un perk attivo di tipo {package.perk_type.value}',
                'existing_perk': existing_perk.to_dict()
            }), 400
        
        # Spendi i punti
        success, transaction = balance.spend_points(
            package.points_cost,
            package.perk_type,
            f"Attivazione {package.name}"
        )
        
        if not success:
            return jsonify({'error': transaction}), 400
        
        # Crea il perk attivo
        active_perk = ActivePerk(
            azienda_id=current_user.id,
            perk_type=package.perk_type,
            points_spent=package.points_cost,
            duration_days=package.duration_days
        )
        
        db.session.add(active_perk)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Perk "{package.name}" attivato con successo!',
            'active_perk': active_perk.to_dict(),
            'transaction': transaction.to_dict(),
            'new_balance': balance.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/active', methods=['GET'])
@cross_origin()
@require_auth()
def get_active_perks(current_user):
    """Ottiene tutti i perk attivi dell'azienda"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono avere perk attivi'}), 403
        
        # Pulisci i perk scaduti
        cleanup_expired_perks()
        
        active_perks = ActivePerk.query.filter_by(
            azienda_id=current_user.id,
            is_active=True
        ).filter(ActivePerk.end_date > datetime.utcnow()).all()
        
        # Calcola il punteggio di priorità
        priority_score = calculate_perk_priority_score(current_user.id)
        
        return jsonify({
            'success': True,
            'active_perks': [perk.to_dict() for perk in active_perks],
            'priority_score': priority_score
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/transactions', methods=['GET'])
@cross_origin()
@require_auth()
def get_transactions_history(current_user):
    """Ottiene la cronologia delle transazioni punti"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono avere transazioni punti'}), 403
        
        # Parametri di paginazione
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        transactions = PerkPointsTransaction.query.filter_by(
            azienda_id=current_user.id
        ).order_by(PerkPointsTransaction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'transactions': [t.to_dict() for t in transactions.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': transactions.total,
                'pages': transactions.pages,
                'has_next': transactions.has_next,
                'has_prev': transactions.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/priority-score/<int:azienda_id>', methods=['GET'])
@cross_origin()
def get_priority_score(azienda_id):
    """Ottiene il punteggio di priorità di un'azienda (per uso interno)"""
    try:
        priority_score = calculate_perk_priority_score(azienda_id)
        
        return jsonify({
            'success': True,
            'azienda_id': azienda_id,
            'priority_score': priority_score
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/deactivate/<int:perk_id>', methods=['POST'])
@cross_origin()
@require_auth()
def deactivate_perk(current_user, perk_id):
    """Disattiva un perk attivo"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono disattivare perk'}), 403
        
        active_perk = ActivePerk.query.filter_by(
            id=perk_id,
            azienda_id=current_user.id,
            is_active=True
        ).first()
        
        if not active_perk:
            return jsonify({'error': 'Perk attivo non trovato'}), 404
        
        active_perk.deactivate()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Perk disattivato con successo',
            'perk': active_perk.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@perk_points_bp.route('/stats', methods=['GET'])
@cross_origin()
@require_auth()
def get_perk_stats(current_user):
    """Ottiene statistiche sui perk dell'azienda"""
    try:
        if current_user.tipo_utente != 'azienda':
            return jsonify({'error': 'Solo le aziende possono avere statistiche perk'}), 403
        
        # Statistiche generali
        balance = PerkPointsBalance.query.filter_by(azienda_id=current_user.id).first()
        
        if not balance:
            balance = PerkPointsBalance(azienda_id=current_user.id)
            db.session.add(balance)
            db.session.commit()
        
        # Perk attivi
        active_perks_count = ActivePerk.query.filter_by(
            azienda_id=current_user.id,
            is_active=True
        ).filter(ActivePerk.end_date > datetime.utcnow()).count()
        
        # Perk scaduti
        expired_perks_count = ActivePerk.query.filter_by(
            azienda_id=current_user.id
        ).filter(ActivePerk.end_date <= datetime.utcnow()).count()
        
        # Transazioni del mese corrente
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_transactions = PerkPointsTransaction.query.filter(
            PerkPointsTransaction.azienda_id == current_user.id,
            PerkPointsTransaction.created_at >= current_month_start
        ).count()
        
        # Punti spesi questo mese
        monthly_spent = db.session.query(
            db.func.sum(PerkPointsTransaction.points)
        ).filter(
            PerkPointsTransaction.azienda_id == current_user.id,
            PerkPointsTransaction.transaction_type == TransactionType.SPEND,
            PerkPointsTransaction.created_at >= current_month_start
        ).scalar() or 0
        
        stats = {
            'balance': balance.to_dict(),
            'active_perks_count': active_perks_count,
            'expired_perks_count': expired_perks_count,
            'monthly_transactions': monthly_transactions,
            'monthly_spent': abs(monthly_spent),
            'priority_score': calculate_perk_priority_score(current_user.id)
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

