#!/usr/bin/env python3
"""
Script per aggiornare il database con la tabella leaderboard
"""

import os
import sys

# Aggiungi il percorso del progetto
sys.path.insert(0, os.path.dirname(__file__))

from src.models.user import db
from src.models.leaderboard import LeaderboardEntry
from src.main import app

def update_database():
    """Aggiorna il database con le nuove tabelle"""
    with app.app_context():
        try:
            # Crea tutte le tabelle (inclusa la nuova leaderboard_entry)
            db.create_all()
            print("✅ Database aggiornato con successo!")
            print("✅ Tabella leaderboard_entry creata")
            
            # Verifica che la tabella sia stata creata
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'leaderboard_entry' in tables:
                print("✅ Tabella leaderboard_entry verificata")
                
                # Mostra le colonne della tabella
                columns = inspector.get_columns('leaderboard_entry')
                print("\n📋 Colonne della tabella leaderboard_entry:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("❌ Errore: Tabella leaderboard_entry non trovata")
                
        except Exception as e:
            print(f"❌ Errore nell'aggiornamento del database: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Aggiornamento database per leaderboard...")
    success = update_database()
    
    if success:
        print("\n🎉 Aggiornamento completato con successo!")
    else:
        print("\n💥 Aggiornamento fallito!")
        sys.exit(1)

