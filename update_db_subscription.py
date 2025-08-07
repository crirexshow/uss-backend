#!/usr/bin/env python3

import os
import sys

# Aggiungi il percorso del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.user import db
from src.models.subscription import Subscription, PlanType, SubscriptionStatus
from flask import Flask

def update_database():
    """Aggiorna il database aggiungendo la tabella subscription"""
    
    # Configura l'app Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inizializza il database
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🔄 Aggiornamento database per sistema abbonamenti...")
            
            # Crea tutte le tabelle (inclusa subscription)
            db.create_all()
            
            print("✅ Tabella 'subscription' creata con successo!")
            print("📋 Struttura tabella subscription:")
            print("   - id (Primary Key)")
            print("   - azienda_id (Foreign Key)")
            print("   - plan_type (basic/pro/premium)")
            print("   - status (active/expired/cancelled/pending)")
            print("   - start_date, end_date, next_billing_date")
            print("   - monthly_price, currency")
            print("   - monthly_requests_limit, monthly_requests_used")
            print("   - last_reset_date")
            print("   - created_at, updated_at")
            
            # Verifica se ci sono aziende esistenti senza abbonamento
            from src.models.user import User
            aziende = db.session.query(User).filter(User.tipo_utente == 'azienda').all()
            
            if aziende:
                print(f"\n🔧 Trovate {len(aziende)} aziende")
                print("   Creazione abbonamenti Basic di default per tutte le aziende...")
                
                for azienda in aziende:
                    # Verifica se l'azienda ha già un abbonamento
                    existing_subscription = Subscription.query.filter_by(azienda_id=azienda.id).first()
                    if not existing_subscription:
                        subscription = Subscription(azienda_id=azienda.id, plan_type=PlanType.BASIC)
                        db.session.add(subscription)
                
                db.session.commit()
                print(f"✅ Verificati abbonamenti per {len(aziende)} aziende")
            else:
                print("\n✅ Nessuna azienda trovata nel database")
            
            print("\n🎉 Aggiornamento database completato con successo!")
            print("\n📊 Piani disponibili:")
            print("   • Basic: €0/mese - 5 richieste/mese")
            print("   • Pro: €29/mese - 50 richieste/mese + analytics")
            print("   • Premium: €99/mese - richieste illimitate + funzionalità avanzate")
            
        except Exception as e:
            print(f"❌ Errore durante l'aggiornamento del database: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = update_database()
    if success:
        print("\n🚀 Il sistema di abbonamenti è ora attivo!")
    else:
        print("\n💥 Aggiornamento fallito!")
        sys.exit(1)

