import logging
from django.utils import timezone

class CustomLogger:
    @staticmethod
    def setup_logging():
        """
        Konfigurácia centrálneho loggingu
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/app_{timezone.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )

    @staticmethod
    def log_user_action(user, action, details=None):
        """
        Zaznamenávanie užívateľských akcií
        """
        logger = logging.getLogger('user_actions')
        log_entry = {
            'user': user.username,
            'action': action,
            'timestamp': timezone.now(),
            'details': details or {}
        }
        logger.info(log_entry)

    @staticmethod
    def log_system_error(error, context=None):
        """
        Zaznamenávanie systémových chýb
        """
        logger = logging.getLogger('system_errors')
        error_entry = {
            'error': str(error),
            'context': context,
            'timestamp': timezone.now()
        }
        logger.error(error_entry)