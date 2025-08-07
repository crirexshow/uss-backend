from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Promotore, Azienda, Richiesta
from datetime import datetime

azienda_bp = Blueprint('azienda', __name__)

def require_azienda():
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    if session.get('tipo_utente') != 'Azienda':
        return jsonify({'error': 'Accesso riservato alle aziende'}), 403
    return None

@azienda_bp.route('/me', methods=['GET'])
def get_azienda_profile():
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    azienda = Azienda.query.get(session['user_id'])
    if not azienda:
        return jsonify({'error': 'Profilo azienda non trovato'}), 404
    
    return jsonify({
        'azienda': azienda.to_dict(),
        'user': azienda.user.to_dict()
    }), 200

@azienda_bp.route('/me', methods=['PUT'])
def update_azienda_profile():
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        azienda = Azienda.query.get(session['user_id'])
        
        if not azienda:
            return jsonify({'error': 'Profilo azienda non trovato'}), 404
        
        # Aggiorna campi azienda
        if 'nome_attivita' in data:
            azienda.nome_attivita = data['nome_attivita']
        if 'tipo_attivita' in data:
            azienda.tipo_attivita = data['tipo_attivita']
        if 'min_visualizzazioni_richieste' in data:
            azienda.min_visualizzazioni_richieste = data['min_visualizzazioni_richieste']
        if 'localita' in data:
            azienda.localita = data['localita']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profilo aggiornato con successo',
            'azienda': azienda.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@azienda_bp.route('/richieste', methods=['GET'])
def get_richieste_ricevute():
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    try:
        stato = request.args.get('stato')  # Filtro opzionale per stato
        
        query = Richiesta.query.filter_by(azienda_id=session['user_id'])
        
        if stato:
            query = query.filter_by(stato=stato)
        
        richieste = query.order_by(Richiesta.data_creazione.desc()).all()
        
        # Aggiungi informazioni sul promotore a ogni richiesta
        richieste_with_promotore = []
        for richiesta in richieste:
            richiesta_dict = richiesta.to_dict()
            richiesta_dict['promotore'] = richiesta.promotore.to_dict()
            richiesta_dict['promotore_user'] = richiesta.promotore.user.to_dict()
            richieste_with_promotore.append(richiesta_dict)
        
        return jsonify({
            'richieste': richieste_with_promotore
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@azienda_bp.route('/richieste/<int:richiesta_id>', methods=['PUT'])
def gestisci_richiesta(richiesta_id):
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        
        if not data.get('azione'):
            return jsonify({'error': 'Azione obbligatoria (accetta, rifiuta, controproposta)'}), 400
        
        richiesta = Richiesta.query.filter_by(
            id=richiesta_id,
            azienda_id=session['user_id']
        ).first()
        
        if not richiesta:
            return jsonify({'error': 'Richiesta non trovata'}), 404
        
        if richiesta.stato != 'In sospeso':
            return jsonify({'error': 'La richiesta è già stata gestita'}), 400
        
        azione = data['azione'].lower()
        
        if azione == 'accetta':
            richiesta.stato = 'Accettata'
            richiesta.messaggio_azienda = data.get('messaggio_azienda', 'Richiesta accettata')
        elif azione == 'rifiuta':
            richiesta.stato = 'Rifiutata'
            richiesta.messaggio_azienda = data.get('messaggio_azienda', 'Richiesta rifiutata')
        elif azione == 'controproposta':
            if not data.get('messaggio_azienda'):
                return jsonify({'error': 'Messaggio obbligatorio per la controproposta'}), 400
            richiesta.stato = 'Controproposta'
            richiesta.messaggio_azienda = data['messaggio_azienda']
        else:
            return jsonify({'error': 'Azione non valida'}), 400
        
        richiesta.data_aggiornamento = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': f'Richiesta {azione}ta con successo',
            'richiesta': richiesta.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@azienda_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    try:
        # Statistiche richieste
        richieste_in_sospeso = Richiesta.query.filter_by(
            azienda_id=session['user_id'],
            stato='In sospeso'
        ).count()
        
        richieste_accettate = Richiesta.query.filter_by(
            azienda_id=session['user_id'],
            stato='Accettata'
        ).count()
        
        richieste_rifiutate = Richiesta.query.filter_by(
            azienda_id=session['user_id'],
            stato='Rifiutata'
        ).count()
        
        richieste_controproposta = Richiesta.query.filter_by(
            azienda_id=session['user_id'],
            stato='Controproposta'
        ).count()
        
        return jsonify({
            'statistiche': {
                'in_sospeso': richieste_in_sospeso,
                'accettate': richieste_accettate,
                'rifiutate': richieste_rifiutate,
                'controproposta': richieste_controproposta
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@azienda_bp.route("/promotori", methods=["GET"])
def get_promotori():
    auth_error = require_azienda()
    if auth_error:
        return auth_error
    
    try:
        # Parametri di ricerca opzionali
        industry = request.args.get("industry")
        instagram_link = request.args.get("instagram_link")
        tiktok_link = request.args.get("tiktok_link")
        linkedin_link = request.args.get("linkedin_link")
        # Aggiungere filtri per follower se implementati nel modello Promotore
        
        query = Promotore.query
        
        if industry:
            query = query.filter(Promotore.industry.ilike(f"%{industry}%"))
        if instagram_link == "true":
            query = query.filter(Promotore.instagram_link.isnot(None))
        if tiktok_link == "true":
            query = query.filter(Promotore.tiktok_link.isnot(None))
        if linkedin_link == "true":
            query = query.filter(Promotore.linkedin_link.isnot(None))
        
        promotori = query.all()
        
        # Prepara i dati dei promotori includendo l'email dell'utente associato
        promotori_data = []
        for promotore in promotori:
            promotore_dict = promotore.to_dict()
            if promotore.user:
                promotore_dict["email"] = promotore.user.email
            promotori_data.append(promotore_dict)
        
        return jsonify({
            "promotori": promotori_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


