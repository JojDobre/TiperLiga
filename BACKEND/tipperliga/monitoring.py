import requests
import logging
from django.utils import timezone
from django.conf import settings



class MonitoringService:
    @staticmethod
    def send_error_to_monitoring(error, context=None):
        """
        Odoslanie chyby do externého monitorovacieho systému
        """
        try:
            payload = {
                'error': str(error),
                'context': context,
                'timestamp': timezone.now().isoformat()
            }
            
            response = requests.post(
                settings.MONITORING_WEBHOOK_URL, 
                json=payload
            )
            
            if response.status_code != 200:
                logging.error("Failed to send error to monitoring")
        except Exception as e:
            logging.error(f"Monitoring webhook error: {e}")