from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Promotore, Azienda, Richiesta
from datetime import datetime
import os

promotore_bp = Blueprint('promotore', __name__)

def require_promotore():
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    if session.get('tipo_utente') != 'Promotore':
        return jsonify({'error': 'Accesso riservato ai promotori'}), 403
    return None

@promotore_bp.route('/me', methods=['GET'])
def get_promotore_profile():
    auth_error = require_promotore()
    if auth_error:
        return auth_error
    
    promotore = Promotore.query.get(session['user_id'])
    if not promotore:
        return jsonify({'error': 'Profilo promotore non trovato'}), 404
    
    return jsonify({
        'promotore': promotore.to_dict(),
        'user': promotore.user.to_dict()
    }), 200

@promotore_bp.route('/me', methods=['PUT'])
def update_promotore_profile():
    auth_error = require_promotore()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        promotore = Promotore.query.get(session['user_id'])
        
        if not promotore:
            return jsonify({'error': 'Profilo promotore non trovato'}), 404
        
        # Aggiorna link social
        if 'instagram_link' in data:
            promotore.instagram_link = data['instagram_link']
        if 'tiktok_link' in data:
            promotore.tiktok_link = data['tiktok_link']
        if 'linkedin_link' in data:
            promotore.linkedin_link = data['linkedin_link']
        
        # Aggiorna percorsi file (in un'implementazione reale, qui gestiresti l'upload dei file)
        if 'insight_screenshot_path' in data:
            promotore.insight_screenshot_path = data['insight_screenshot_path']
        if 'foto_visualizzazioni_1_path' in data:
            promotore.foto_visualizzazioni_1_path = data['foto_visualizzazioni_1_path']
        if 'foto_visualizzazioni_2_path' in data:
            promotore.foto_visualizzazioni_2_path = data['foto_visualizzazioni_2_path']
        if 'foto_visualizzazioni_3_path' in data:
            promotore.foto_visualizzazioni_3_path = data['foto_visualizzazioni_3_path']
        
        # Aggiorna data ultimo aggiornamento insight
        if any(key in data for key in ['insight_screenshot_path', 'foto_visualizzazioni_1_path', 'foto_visualizzazioni_2_path', 'foto_visualizzazioni_3_path']):
            promotore.ultimo_aggiornamento_insight = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profilo aggiornato con successo',
            'promotore': promotore.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@promotore_bp.route('/aziende', methods=['GET'])
def get_aziende():
    auth_error = require_promotore()
    if auth_error:
        return auth_error
    
    try:
        # Parametri di ricerca opzionali
        tipo_attivita = request.args.get("tipo_attivita")
        localita = request.args.get("localita")
        min_visualizzazioni = request.args.get("min_visualizzazioni")
        nome_attivita = request.args.get("nome_attivita")
        
        query = Azienda.query
        
        if tipo_attivita:
            query = query.filter(Azienda.tipo_attivita.ilike(f"%{tipo_attivita}%"))
        if localita:
            query = query.filter(Azienda.localita.ilike(f"%{localita}%"))
        if min_visualizzazioni:
            query = query.filter(Azienda.min_visualizzazioni_richieste <= int(min_visualizzazioni))
        if nome_attivita:
            query = query.filter(Azienda.nome_attivita.ilike(f"%{nome_attivita}%"))
        
        aziende = query.all()
        
        return jsonify({
            'aziende': [azienda.to_dict() for azienda in aziende]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@promotore_bp.route('/richieste', methods=['POST'])
def invia_richiesta():
    auth_error = require_promotore()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        
        if not data.get('azienda_id') or not data.get('messaggio_promotore'):
            return jsonify({'error': 'ID azienda e messaggio sono obbligatori'}), 400
        
        # Verifica che l'azienda esista
        azienda = Azienda.query.get(data['azienda_id'])
        if not azienda:
            return jsonify({'error': 'Azienda non trovata'}), 404
        
        # Verifica che non esista già una richiesta in sospeso
        existing_request = Richiesta.query.filter_by(
            promotore_id=session['user_id'],
            azienda_id=data['azienda_id'],
            stato='In sospeso'
        ).first()
        
        if existing_request:
            return jsonify({'error': 'Hai già una richiesta in sospeso per questa azienda'}), 400
        
        richiesta = Richiesta(
            promotore_id=session['user_id'],
            azienda_id=data['azienda_id'],
            messaggio_promotore=data['messaggio_promotore']
        )
        
        db.session.add(richiesta)
        db.session.commit()
        
        return jsonify({
            'message': 'Richiesta inviata con successo',
            'richiesta': richiesta.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@promotore_bp.route('/richieste', methods=['GET'])
def get_richieste_inviate():
    auth_error = require_promotore()
    if auth_error:
        return auth_error
    
    try:
        stato = request.args.get('stato')  # Filtro opzionale per stato
        
        query = Richiesta.query.filter_by(promotore_id=session['user_id'])
        
        if stato:
            query = query.filter_by(stato=stato)
        
        richieste = query.order_by(Richiesta.data_creazione.desc()).all()
        
        # Aggiungi informazioni sull'azienda a ogni richiesta
        richieste_with_azienda = []
        for richiesta in richieste:
            richiesta_dict = richiesta.to_dict()
            richiesta_dict['azienda'] = richiesta.azienda.to_dict()
            richieste_with_azienda.append(richiesta_dict)
        
        return jsonify({
            'richieste': richieste_with_azienda
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

