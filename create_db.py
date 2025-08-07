#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from src.models.user import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Assicurati che la directory database esista
os.makedirs(os.path.join(os.path.dirname(__file__), 'src', 'database'), exist_ok=True)

db.init_app(app)

with app.app_context():
    print("Creazione del database...")
    db.create_all()
    print("Database creato con successo!")
    
    # Verifica le tabelle create
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tabelle create: {tables}")
    
    # Verifica le colonne della tabella user
    if 'user' in tables:
        columns = inspector.get_columns('user')
        print("Colonne della tabella 'user':")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")

