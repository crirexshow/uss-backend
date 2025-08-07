import schedule
import time
import threading
import requests
from datetime import datetime
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CronJobManager:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.running = False
        self.thread = None
    
    def start(self):
        """Avvia il sistema di cron job"""
        if self.running:
            logger.warning("Cron job manager già in esecuzione")
            return
        
        self.running = True
        
        # Schedula i job
        self.schedule_jobs()
        
        # Avvia il thread per l'esecuzione
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Cron job manager avviato")
    
    def stop(self):
        """Ferma il sistema di cron job"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Cron job manager fermato")
    
    def schedule_jobs(self):
        """Configura tutti i job schedulati"""
        
        # Aggiornamento leaderboard ogni giorno alle 02:00
        schedule.every().day.at("02:00").do(self.update_leaderboard_job)
        
        # Aggiornamento leaderboard ogni ora (per test e aggiornamenti frequenti)
        schedule.every().hour.do(self.update_leaderboard_job)
        
        # Job di test ogni 5 minuti (solo per sviluppo)
        # schedule.every(5).minutes.do(self.test_job)
        
        logger.info("Job schedulati configurati")
    
    def _run_scheduler(self):
        """Esegue il loop del scheduler"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Controlla ogni minuto
            except Exception as e:
                logger.error(f"Errore nel scheduler: {e}")
                time.sleep(60)
    
    def update_leaderboard_job(self):
        """Job per aggiornare la leaderboard"""
        try:
            logger.info("Avvio aggiornamento leaderboard...")
            
            # Chiama l'API per aggiornare la leaderboard
            response = requests.post(f"{self.base_url}/api/leaderboard/update-all")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Leaderboard aggiornata: {data.get('message', 'Successo')}")
            else:
                logger.error(f"Errore nell'aggiornamento leaderboard: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Errore nel job di aggiornamento leaderboard: {e}")
    
    def test_job(self):
        """Job di test"""
        logger.info(f"Test job eseguito alle {datetime.now()}")
    
    def get_scheduled_jobs(self):
        """Restituisce la lista dei job schedulati"""
        jobs = []
        for job in schedule.jobs:
            jobs.append({
                'job': str(job.job_func),
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'interval': str(job.interval),
                'unit': job.unit
            })
        return jobs

# Istanza globale del manager
cron_manager = CronJobManager()

def start_cron_jobs():
    """Funzione per avviare i cron job"""
    cron_manager.start()

def stop_cron_jobs():
    """Funzione per fermare i cron job"""
    cron_manager.stop()

def get_cron_status():
    """Restituisce lo stato dei cron job"""
    return {
        'running': cron_manager.running,
        'scheduled_jobs': cron_manager.get_scheduled_jobs()
    }

