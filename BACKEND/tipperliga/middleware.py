import logging
from django.utils import timezone
from .user_activity import UserActivityService

logger = logging.getLogger(__name__)

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Pred spracovaním requestu
        if request.user.is_authenticated:
            request.user.last_login = timezone.now()
            request.user.save(update_fields=['last_login'])
        
        # Zaznamenanie requestu
        logger.info(f"Path: {request.path}, Method: {request.method}, User: {request.user}")
        
        response = self.get_response(request)
        return response
    
class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Spracovanie requestu pred view
        response = self.get_response(request)
        
        # Zaznamenanie aktivity pre prihlásených užívateľov
        if request.user.is_authenticated:
            # Sledovanie zariadenia
            UserActivityService.track_device(request.user, request)
            
            # Príklady logovania aktivít
            if request.method == 'POST':
                # Príklad: Logovanie umiestnenia tipu
                if request.path.endswith('/bets/place/'):
                    UserActivityService.log_activity(
                        request.user, 
                        'bet_placed', 
                        request=request
                    )
                
                # Príklad: Logovanie zmeny profilu
                if request.path.endswith('/profile/update/'):
                    UserActivityService.log_activity(
                        request.user, 
                        'profile_update', 
                        request=request
                    )
        
        return response