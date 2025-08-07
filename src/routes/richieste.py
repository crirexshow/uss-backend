from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Promotore, Azienda, Richiesta
from src.models.messaggio import Messaggio
from datetime import datetime

richieste_bp = Blueprint('richieste', __name__)

@richieste_bp.route('/invia', methods=['POST'])
def invia_richiesta():
    """Invia una nuova richiesta da un content creator a un'azienda"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.tipo_utente != 'Promotore':
            return jsonify({'error': 'Solo i content creator possono inviare richieste'}), 403
        
        data = request.get_json()
        if not data.get('azienda_id') or not data.get('messaggio'):
            return jsonify({'error': 'ID azienda e messaggio sono obbligatori'}), 400
        
        # Verifica che l'azienda esista
        azienda = Azienda.query.get(data['azienda_id'])
        if not azienda:
            return jsonify({'error': 'Azienda non trovata'}), 404
        
        # Verifica che non esista già una richiesta attiva
        richiesta_esistente = Richiesta.query.filter_by(
            promotore_id=user.id,
            azienda_id=data['azienda_id']
        ).filter(Richiesta.stato.in_(['In sospeso', 'In negoziazione'])).first()
        
        if richiesta_esistente:
            return jsonify({'error': 'Hai già una richiesta attiva con questa azienda'}), 400
        
        # Crea la nuova richiesta
        richiesta = Richiesta(
            promotore_id=user.id,
            azienda_id=data['azienda_id'],
            messaggio_iniziale=data['messaggio'],
            stato='In sospeso'
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

@richieste_bp.route('/messaggio', methods=['POST'])
def invia_messaggio():
    """Invia un messaggio in una richiesta esistente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        data = request.get_json()
        
        if not data.get('richiesta_id') or not data.get('contenuto'):
            return jsonify({'error': 'ID richiesta e contenuto sono obbligatori'}), 400
        
        richiesta = Richiesta.query.get(data['richiesta_id'])
        if not richiesta:
            return jsonify({'error': 'Richiesta non trovata'}), 404
        
        # Verifica che l'utente sia coinvolto nella richiesta
        if user.tipo_utente == 'Promotore' and richiesta.promotore_id != user.id:
            return jsonify({'error': 'Non autorizzato'}), 403
        elif user.tipo_utente == 'Azienda' and richiesta.azienda_id != user.id:
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Determina il tipo di messaggio
        tipo_messaggio = data.get('tipo_messaggio', 'messaggio')
        if tipo_messaggio not in ['messaggio', 'controproposta', 'accettazione', 'rifiuto']:
            tipo_messaggio = 'messaggio'
        
        # Crea il messaggio
        messaggio = Messaggio(
            richiesta_id=richiesta.id,
            mittente_tipo=user.tipo_utente.lower(),
            mittente_id=user.id,
            contenuto=data['contenuto'],
            tipo_messaggio=tipo_messaggio
        )
        
        # Aggiorna lo stato della richiesta in base al tipo di messaggio
        if tipo_messaggio == 'accettazione':
            richiesta.stato = 'Accettata'
            richiesta.data_accettazione = datetime.utcnow()
        elif tipo_messaggio == 'rifiuto':
            richiesta.stato = 'Rifiutata'
        elif tipo_messaggio == 'controproposta':
            richiesta.stato = 'In negoziazione'
        elif richiesta.stato == 'In sospeso':
            richiesta.stato = 'In negoziazione'
        
        richiesta.data_aggiornamento = datetime.utcnow()
        
        db.session.add(messaggio)
        db.session.commit()
        
        return jsonify({
            'message': 'Messaggio inviato con successo',
            'messaggio': messaggio.to_dict(),
            'richiesta': richiesta.to_dict(include_sensitive_data=(richiesta.stato == 'Accettata'))
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@richieste_bp.route('/lista', methods=['GET'])
def get_richieste():
    """Ottiene la lista delle richieste per l'utente corrente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        stato_filter = request.args.get('stato')
        
        if user.tipo_utente == 'Promotore':
            query = Richiesta.query.filter_by(promotore_id=user.id)
        else:
            query = Richiesta.query.filter_by(azienda_id=user.id)
        
        if stato_filter:
            query = query.filter_by(stato=stato_filter)
        
        richieste = query.order_by(Richiesta.data_aggiornamento.desc()).all()
        
        # Include dati sensibili solo per richieste accettate
        richieste_data = []
        for richiesta in richieste:
            include_sensitive = (richiesta.stato == 'Accettata')
            richieste_data.append(richiesta.to_dict(include_sensitive_data=include_sensitive))
        
        return jsonify({'richieste': richieste_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@richieste_bp.route('/<int:richiesta_id>/messaggi', methods=['GET'])
def get_messaggi_richiesta(richiesta_id):
    """Ottiene tutti i messaggi di una richiesta"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        richiesta = Richiesta.query.get(richiesta_id)
        
        if not richiesta:
            return jsonify({'error': 'Richiesta non trovata'}), 404
        
        # Verifica che l'utente sia coinvolto nella richiesta
        if user.tipo_utente == 'Promotore' and richiesta.promotore_id != user.id:
            return jsonify({'error': 'Non autorizzato'}), 403
        elif user.tipo_utente == 'Azienda' and richiesta.azienda_id != user.id:
            return jsonify({'error': 'Non autorizzato'}), 403
        
        messaggi = Messaggio.query.filter_by(richiesta_id=richiesta_id).order_by(Messaggio.data_creazione.asc()).all()
        
        return jsonify({
            'richiesta': richiesta.to_dict(include_sensitive_data=(richiesta.stato == 'Accettata')),
            'messaggi': [msg.to_dict() for msg in messaggi]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

