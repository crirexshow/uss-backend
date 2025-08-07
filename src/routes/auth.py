from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Promotore, Azienda
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validazione dati base
        if not data.get('email') or not data.get('password') or not data.get('tipo_utente'):
            return jsonify({'error': 'Email, password e tipo utente sono obbligatori'}), 400
        
        if data['tipo_utente'] not in ['Promotore', 'Azienda']:
            return jsonify({'error': 'Tipo utente deve essere Promotore o Azienda'}), 400
        
        # Verifica se l'utente esiste già
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email già registrata'}), 400
        
        # Crea nuovo utente
        user = User(
            email=data['email'],
            tipo_utente=data['tipo_utente']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Per ottenere l'ID dell'utente
        
        # Crea profilo specifico in base al tipo utente
        if data['tipo_utente'] == 'Promotore':
            # Validazione per promotore
            social_links = [data.get('instagram_link'), data.get('tiktok_link'), data.get('linkedin_link')]
            if not any(social_links):
                return jsonify({'error': 'Almeno un link social è obbligatorio per i promotori'}), 400
            
            if not data.get('industry'):
                return jsonify({'error': 'Il campo industry è obbligatorio per i content creator'}), 400
            
            # Validazione industry
            valid_industries = ['Beauty', 'Food & Restaurant', 'Fashion', 'Travel', 'Tech', 'Other']
            industry = data.get('industry')
            if industry not in valid_industries:
                # Se è "Other", deve essere fornito un valore personalizzato
                if not data.get('custom_industry'):
                    return jsonify({'error': 'Per "Other" è necessario specificare un industry personalizzato'}), 400
                industry = data.get('custom_industry')[:30]  # Limita a 30 caratteri
            
            promotore = Promotore(
                id=user.id,
                industry=industry,
                instagram_link=data.get('instagram_link'),
                tiktok_link=data.get('tiktok_link'),
                linkedin_link=data.get('linkedin_link')
            )
            db.session.add(promotore)
            
        elif data['tipo_utente'] == 'Azienda':
            # Validazione per azienda
            if not data.get('nome_attivita') or not data.get('tipo_attivita') or not data.get('localita'):
                return jsonify({'error': 'Nome attività, tipo attività e località sono obbligatori per le aziende'}), 400
            
            azienda = Azienda(
                id=user.id,
                nome_attivita=data['nome_attivita'],
                tipo_attivita=data['tipo_attivita'],
                min_visualizzazioni_richieste=data.get('min_visualizzazioni_richieste'),
                localita=data['localita']
            )
            db.session.add(azienda)
        
        db.session.commit()
        
        # Login automatico dopo registrazione
        session['user_id'] = user.id
        session['tipo_utente'] = user.tipo_utente
        
        return jsonify({
            'message': 'Registrazione completata con successo',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email e password sono obbligatori'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Credenziali non valide'}), 401
        
        session['user_id'] = user.id
        session['tipo_utente'] = user.tipo_utente
        
        return jsonify({
            'message': 'Login effettuato con successo',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout effettuato con successo'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Utente non trovato'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

