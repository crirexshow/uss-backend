#!/usr/bin/env python3

import os
import sys

# Aggiungi il percorso del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.user import db, User
from src.models.perk_points import (
    PerkPointsBalance, PerkPointsTransaction, ActivePerk, PerkPackage,
    PerkType, TransactionType
)
from flask import Flask

def update_database():
    """Aggiorna il database aggiungendo le tabelle per il sistema Perk Points"""
    
    # Configura l'app Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inizializza il database
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🔄 Aggiornamento database per sistema Perk Points...")
            
            # Crea tutte le tabelle (incluse quelle per perk points)
            db.create_all()
            
            print("✅ Tabelle Perk Points create con successo!")
            print("📋 Struttura tabelle create:")
            print("   • perk_points_balance - Saldi punti delle aziende")
            print("   • perk_points_transaction - Cronologia transazioni")
            print("   • active_perk - Perk attivi delle aziende")
            print("   • perk_package - Pacchetti perk disponibili")
            
            # Crea i pacchetti perk di default se non esistono
            existing_packages = PerkPackage.query.count()
            
            if existing_packages == 0:
                print("\n🔧 Creazione pacchetti perk di default...")
                
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
                print(f"✅ Creati {len(default_packages)} pacchetti perk di default")
            else:
                print(f"\n✅ Trovati {existing_packages} pacchetti perk esistenti")
            
            # Verifica se ci sono aziende esistenti senza saldo punti
            aziende = db.session.query(User).filter(User.tipo_utente == 'azienda').all()
            
            if aziende:
                print(f"\n🔧 Trovate {len(aziende)} aziende")
                print("   Creazione saldi punti di default...")
                
                created_balances = 0
                for azienda in aziende:
                    # Verifica se l'azienda ha già un saldo punti
                    existing_balance = PerkPointsBalance.query.filter_by(azienda_id=azienda.id).first()
                    if not existing_balance:
                        balance = PerkPointsBalance(azienda_id=azienda.id)
                        db.session.add(balance)
                        created_balances += 1
                
                if created_balances > 0:
                    db.session.commit()
                    print(f"✅ Creati {created_balances} saldi punti di default")
                else:
                    print("✅ Tutte le aziende hanno già un saldo punti")
            else:
                print("\n✅ Nessuna azienda trovata nel database")
            
            print("\n🎉 Aggiornamento database completato con successo!")
            print("\n📊 Sistema Perk Points attivo:")
            print("   🎯 Listing Prioritario - 100 punti (30 giorni)")
            print("   ⭐ Profilo in Evidenza - 150 punti (30 giorni)")
            print("   🚀 Boost Visibilità - 75 punti (7 giorni)")
            print("   👑 Badge Premium - 200 punti (60 giorni)")
            
            print("\n💰 Prezzi punti:")
            print("   • 100 punti - €9.99")
            print("   • 250 punti + 25 bonus - €19.99 (Popolare)")
            print("   • 500 punti + 75 bonus - €34.99")
            print("   • 1000 punti + 200 bonus - €59.99")
            
        except Exception as e:
            print(f"❌ Errore durante l'aggiornamento del database: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = update_database()
    if success:
        print("\n🚀 Il sistema Perk Points è ora attivo!")
    else:
        print("\n💥 Aggiornamento fallito!")
        sys.exit(1)

