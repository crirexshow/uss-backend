from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.user import db, User, Promotore, Azienda
import os
from werkzeug.utils import secure_filename

settings_bp = Blueprint('settings', __name__)

UPLOAD_FOLDER = 'uploads/screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@settings_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Aggiorna il profilo utente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        data = request.get_json()
        
        # Aggiorna email se fornita
        if 'email' in data and data['email'] != user.email:
            # Verifica che l'email non sia già in uso
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email già in uso'}), 400
            user.email = data['email']
        
        # Aggiorna dati specifici per tipo utente
        if user.tipo_utente == 'Promotore':
            promotore = Promotore.query.filter_by(user_id=user.id).first()
            if promotore:
                if 'industry' in data:
                    promotore.industry = data['industry']
                if 'custom_industry' in data:
                    promotore.custom_industry = data['custom_industry']
                if 'instagram_link' in data:
                    promotore.instagram_link = data['instagram_link']
                if 'tiktok_link' in data:
                    promotore.tiktok_link = data['tiktok_link']
                if 'linkedin_link' in data:
                    promotore.linkedin_link = data['linkedin_link']
        
        elif user.tipo_utente == 'Azienda':
            azienda = Azienda.query.filter_by(user_id=user.id).first()
            if azienda:
                if 'nome_attivita' in data:
                    azienda.nome_attivita = data['nome_attivita']
                if 'tipo_attivita' in data:
                    azienda.tipo_attivita = data['tipo_attivita']
                if 'localita' in data:
                    azienda.localita = data['localita']
                if 'min_visualizzazioni_richieste' in data:
                    azienda.min_visualizzazioni_richieste = data['min_visualizzazioni_richieste']
        
        db.session.commit()
        
        return jsonify({'message': 'Profilo aggiornato con successo'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/password', methods=['PUT'])
def change_password():
    """Cambia la password dell'utente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Password attuale e nuova password sono obbligatorie'}), 400
        
        # Verifica password attuale
        if not check_password_hash(user.password_hash, data['current_password']):
            return jsonify({'error': 'Password attuale non corretta'}), 400
        
        # Aggiorna password
        user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password cambiata con successo'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/screenshots', methods=['POST'])
def upload_screenshots():
    """Carica screenshot degli insights (solo per content creator)"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.tipo_utente != 'Promotore':
            return jsonify({'error': 'Solo i content creator possono caricare screenshot'}), 403
        
        # Crea directory se non esiste
        upload_path = os.path.join(UPLOAD_FOLDER, str(user.id))
        os.makedirs(upload_path, exist_ok=True)
        
        uploaded_files = []
        
        for key in request.files:
            file = request.files[key]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Aggiungi timestamp per evitare conflitti
                import time
                timestamp = str(int(time.time()))
                filename = f"{timestamp}_{filename}"
                
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                uploaded_files.append({
                    'filename': filename,
                    'path': file_path,
                    'url': f'/uploads/screenshots/{user.id}/{filename}'
                })
        
        if not uploaded_files:
            return jsonify({'error': 'Nessun file valido caricato'}), 400
        
        return jsonify({
            'message': f'{len(uploaded_files)} screenshot caricati con successo',
            'files': uploaded_files
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/screenshots', methods=['GET'])
def get_screenshots():
    """Ottiene la lista degli screenshot caricati"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.tipo_utente != 'Promotore':
            return jsonify({'error': 'Solo i content creator possono visualizzare screenshot'}), 403
        
        upload_path = os.path.join(UPLOAD_FOLDER, str(user.id))
        screenshots = []
        
        if os.path.exists(upload_path):
            for filename in os.listdir(upload_path):
                if allowed_file(filename):
                    screenshots.append({
                        'filename': filename,
                        'url': f'/uploads/screenshots/{user.id}/{filename}'
                    })
        
        return jsonify({'screenshots': screenshots}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/account', methods=['DELETE'])
def delete_account():
    """Elimina l'account utente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Elimina dati correlati
        if user.tipo_utente == 'Promotore':
            promotore = Promotore.query.filter_by(user_id=user.id).first()
            if promotore:
                # Elimina richieste associate
                from src.models.user import Richiesta
                from src.models.messaggio import Messaggio
                
                richieste = Richiesta.query.filter_by(promotore_id=promotore.id).all()
                for richiesta in richieste:
                    # Elimina messaggi associati
                    Messaggio.query.filter_by(richiesta_id=richiesta.id).delete()
                    db.session.delete(richiesta)
                
                db.session.delete(promotore)
        
        elif user.tipo_utente == 'Azienda':
            azienda = Azienda.query.filter_by(user_id=user.id).first()
            if azienda:
                # Elimina richieste associate
                from src.models.user import Richiesta
                from src.models.messaggio import Messaggio
                
                richieste = Richiesta.query.filter_by(azienda_id=azienda.id).all()
                for richiesta in richieste:
                    # Elimina messaggi associati
                    Messaggio.query.filter_by(richiesta_id=richiesta.id).delete()
                    db.session.delete(richiesta)
                
                db.session.delete(azienda)
        
        # Elimina screenshot se esistono
        upload_path = os.path.join(UPLOAD_FOLDER, str(user.id))
        if os.path.exists(upload_path):
            import shutil
            shutil.rmtree(upload_path)
        
        # Elimina utente
        db.session.delete(user)
        db.session.commit()
        
        # Rimuovi dalla sessione
        session.clear()
        
        return jsonify({'message': 'Account eliminato con successo'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

