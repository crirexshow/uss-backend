import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.models.leaderboard import LeaderboardEntry  # Import del modello leaderboard
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.promotore import promotore_bp
from src.routes.azienda import azienda_bp
from src.routes.richieste import richieste_bp
from src.routes.settings import settings_bp
from src.routes.leaderboard import leaderboard_bp
from src.routes.subscription import subscription_bp
from src.routes.perk_points import perk_points_bp
from src.cron_jobs import start_cron_jobs
import atexit

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Abilita CORS per tutte le route
CORS(app, supports_credentials=True)

# Registra i blueprint
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(promotore_bp, url_prefix='/api/promotore')
app.register_blueprint(azienda_bp, url_prefix='/api/azienda')
app.register_blueprint(richieste_bp, url_prefix='/api/richieste')
app.register_blueprint(settings_bp, url_prefix='/api/settings')
app.register_blueprint(leaderboard_bp, url_prefix='/api/leaderboard')
app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
app.register_blueprint(perk_points_bp, url_prefix='/api/perk-points')

# Configurazione database
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres.rfwwpmwdpzgbtkdoosmg:Cicciogamer89!!@aws-0-eu-north-1.pooler.supabase.com:6543/postgres"



db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    # Avvia i cron job
    start_cron_jobs()
    
    # Registra la funzione di cleanup per fermare i cron job alla chiusura
    from src.cron_jobs import stop_cron_jobs
    atexit.register(stop_cron_jobs)
    
    app.run(host='0.0.0.0', port=8000, debug=True)

