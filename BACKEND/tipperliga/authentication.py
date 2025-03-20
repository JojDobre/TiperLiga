from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import CustomUser

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            # Štandardná JWT autentifikácia
            authenticated = super().authenticate(request)
            
            if authenticated:
                user, token = authenticated
                
                # Dodatočné kontroly
                if user.is_active == False:
                    raise AuthenticationFailed('Užívateľský účet je neaktívny')
                
                return (user, token)
            
            return None
        
        except Exception as e:
            # Logovanie chýb
            print(f"Authentication error: {e}")
            return None

def generate_tokens(user):
    """
    Generovanie JWT tokenov pre užívateľa
    """
    refresh = RefreshToken.for_user(user)
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
    }