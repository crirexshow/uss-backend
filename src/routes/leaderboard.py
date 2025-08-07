from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Promotore, Richiesta
from src.models.leaderboard import LeaderboardEntry
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import calendar

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/current', methods=['GET'])
def get_current_leaderboard():
    """Ottiene la leaderboard del mese corrente"""
    try:
        mese, anno = LeaderboardEntry.get_current_month_year()
        
        # Ottieni le entry del mese corrente ordinate per punteggio
        entries = LeaderboardEntry.query.filter_by(
            mese=mese,
            anno=anno
        ).join(Promotore).join(User).order_by(
            desc(LeaderboardEntry.punteggio_totale)
        ).all()
        
        # Aggiorna le posizioni
        for i, entry in enumerate(entries, 1):
            entry.posizione = i
        
        db.session.commit()
        
        # Converti in dizionario
        leaderboard_data = []
        for entry in entries[:50]:  # Top 50
            entry_dict = entry.to_dict()
            # Aggiungi dati aggiuntivi del promotore
            if entry.promotore and entry.promotore.user:
                entry_dict['promotore_email_masked'] = mask_email(entry.promotore.user.email)
                entry_dict['promotore_industry'] = entry.promotore.industry
        
            leaderboard_data.append(entry_dict)
        
        return jsonify({
            'leaderboard': leaderboard_data,
            'mese': mese,
            'anno': anno,
            'nome_mese': calendar.month_name[mese],
            'total_entries': len(entries)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@leaderboard_bp.route('/history', methods=['GET'])
def get_leaderboard_history():
    """Ottiene la storia della leaderboard per mesi precedenti"""
    try:
        mese = request.args.get('mese', type=int)
        anno = request.args.get('anno', type=int)
        
        if not mese or not anno:
            return jsonify({'error': 'Mese e anno sono obbligatori'}), 400
        
        # Ottieni le entry del mese specificato
        entries = LeaderboardEntry.query.filter_by(
            mese=mese,
            anno=anno
        ).join(Promotore).join(User).order_by(
            desc(LeaderboardEntry.punteggio_totale)
        ).limit(50).all()
        
        leaderboard_data = []
        for entry in entries:
            entry_dict = entry.to_dict()
            if entry.promotore and entry.promotore.user:
                entry_dict['promotore_email_masked'] = mask_email(entry.promotore.user.email)
                entry_dict['promotore_industry'] = entry.promotore.industry
            
            leaderboard_data.append(entry_dict)
        
        return jsonify({
            'leaderboard': leaderboard_data,
            'mese': mese,
            'anno': anno,
            'nome_mese': calendar.month_name[mese],
            'total_entries': len(entries)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@leaderboard_bp.route('/my-position', methods=['GET'])
def get_my_position():
    """Ottiene la posizione dell'utente corrente nella leaderboard"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or user.tipo_utente != 'promotore':
            return jsonify({'error': 'Solo i content creator hanno una posizione in leaderboard'}), 403
        
        promotore = Promotore.query.filter_by(user_id=user.id).first()
        if not promotore:
            return jsonify({'error': 'Profilo content creator non trovato'}), 404
        
        mese, anno = LeaderboardEntry.get_current_month_year()
        
        # Ottieni o crea l'entry per l'utente corrente
        entry = LeaderboardEntry.get_or_create_entry(promotore.id, mese, anno)
        
        # Aggiorna le metriche dell'utente
        update_promotore_metrics(promotore.id, mese, anno)
        
        # Ricalcola il punteggio
        entry.calcola_punteggio()
        db.session.commit()
        
        # Calcola la posizione
        entries_above = LeaderboardEntry.query.filter_by(
            mese=mese,
            anno=anno
        ).filter(
            LeaderboardEntry.punteggio_totale > entry.punteggio_totale
        ).count()
        
        entry.posizione = entries_above + 1
        db.session.commit()
        
        return jsonify({
            'entry': entry.to_dict(),
            'posizione': entry.posizione,
            'punteggio': entry.punteggio_totale
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@leaderboard_bp.route('/update-all', methods=['POST'])
def update_all_leaderboard():
    """Aggiorna tutte le entry della leaderboard del mese corrente (per cron job)"""
    try:
        mese, anno = LeaderboardEntry.get_current_month_year()
        
        # Ottieni tutti i promotori attivi
        promotori = Promotore.query.join(User).all()
        
        updated_count = 0
        for promotore in promotori:
            # Ottieni o crea l'entry
            entry = LeaderboardEntry.get_or_create_entry(promotore.id, mese, anno)
            
            # Aggiorna le metriche
            update_promotore_metrics(promotore.id, mese, anno)
            
            # Ricalcola il punteggio
            entry.calcola_punteggio()
            updated_count += 1
        
        # Aggiorna le posizioni
        entries = LeaderboardEntry.query.filter_by(
            mese=mese,
            anno=anno
        ).order_by(desc(LeaderboardEntry.punteggio_totale)).all()
        
        for i, entry in enumerate(entries, 1):
            entry.posizione = i
        
        db.session.commit()
        
        return jsonify({
            'message': f'Leaderboard aggiornata per {updated_count} content creator',
            'mese': mese,
            'anno': anno,
            'updated_count': updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def update_promotore_metrics(promotore_id, mese, anno):
    """Aggiorna le metriche di un promotore per il mese specificato"""
    try:
        # Calcola il primo e ultimo giorno del mese
        primo_giorno = datetime(anno, mese, 1)
        if mese == 12:
            ultimo_giorno = datetime(anno + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_giorno = datetime(anno, mese + 1, 1) - timedelta(days=1)
        
        # Ottieni l'entry
        entry = LeaderboardEntry.query.filter_by(
            promotore_id=promotore_id,
            mese=mese,
            anno=anno
        ).first()
        
        if not entry:
            return
        
        # Conta le richieste inviate nel mese
        richieste_inviate = Richiesta.query.filter(
            Richiesta.promotore_id == promotore_id,
            Richiesta.data_richiesta >= primo_giorno,
            Richiesta.data_richiesta <= ultimo_giorno
        ).count()
        
        # Conta le richieste accettate nel mese
        richieste_accettate = Richiesta.query.filter(
            Richiesta.promotore_id == promotore_id,
            Richiesta.stato == 'Accettata',
            Richiesta.data_accettazione >= primo_giorno,
            Richiesta.data_accettazione <= ultimo_giorno
        ).count()
        
        # Conta le collaborazioni completate (per ora usiamo le accettate)
        collaborazioni_completate = richieste_accettate
        
        # Calcola rating medio (per ora fisso a 4.0, da implementare sistema di rating)
        rating_medio = 4.0
        
        # Calcola giorni attivi (per ora usiamo i giorni con richieste)
        giorni_con_richieste = db.session.query(
            func.count(func.distinct(func.date(Richiesta.data_richiesta)))
        ).filter(
            Richiesta.promotore_id == promotore_id,
            Richiesta.data_richiesta >= primo_giorno,
            Richiesta.data_richiesta <= ultimo_giorno
        ).scalar() or 0
        
        # Aggiorna l'entry
        entry.richieste_inviate = richieste_inviate
        entry.richieste_accettate = richieste_accettate
        entry.collaborazioni_completate = collaborazioni_completate
        entry.rating_medio = rating_medio
        entry.giorni_attivo = giorni_con_richieste
        entry.data_aggiornamento = datetime.utcnow()
        
    except Exception as e:
        print(f"Errore nell'aggiornamento metriche per promotore {promotore_id}: {e}")

def mask_email(email):
    """Maschera l'email per la privacy"""
    if not email or '@' not in email:
        return '***@***.***'
    
    local, domain = email.split('@', 1)
    
    # Maschera la parte locale
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    # Maschera il dominio
    if '.' in domain:
        domain_parts = domain.split('.')
        masked_domain = '*' * len(domain_parts[0]) + '.' + domain_parts[-1]
    else:
        masked_domain = '*' * len(domain)
    
    return f"{masked_local}@{masked_domain}"

