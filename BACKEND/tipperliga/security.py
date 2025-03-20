import secrets
import string
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import models
import pyotp

class PasswordResetToken(models.Model):
    """
    Model pre tokeny na obnovenie hesla
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

class TwoFactorAuthentication(models.Model):
    """
    Model pre dvojfaktorovú autentifikáciu
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=32, null=True, blank=True)
    backup_codes = models.JSONField(default=list)

class SecurityService:
    """
    Servisná trieda pre bezpečnostné operácie
    """
    @staticmethod
    def generate_strong_password(length=16):
        """
        Generovanie silného hesla
        """
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    def validate_password(password):
        """
        Validácia hesla podľa bezpečnostných kritérií
        """
        # Minimálna dĺžka
        if len(password) < 8:
            return False, "Heslo musí mať aspoň 8 znakov"
        
        # Kontrola zložitosti
        has_uppercase = any(c.isupper() for c in password)
        has_lowercase = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in string.punctuation for c in password)
        
        if not (has_uppercase and has_lowercase and has_digit and has_special):
            return False, "Heslo musí obsahovať veľké a malé písmená, čísla a špeciálne znaky"
        
        return True, "Heslo je platné"

    @staticmethod
    def initiate_password_reset(user):
        """
        Inicializácia procesu obnovenia hesla
        """
        # Vygenerovanie tokenu
        token = secrets.token_urlsafe(32)
        
        # Vytvorenie záznamu o resete hesla
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            is_used=False
        )
        
        # Odoslanie emailu
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_mail(
            'Obnovenie hesla',
            f'Pre obnovenie hesla kliknite na tento odkaz: {reset_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return reset_token

    @staticmethod
    def reset_password(token, new_password):
        """
        Obnovenie hesla pomocou tokenu
        """
        try:
            # Overenie tokenu
            reset_token = PasswordResetToken.objects.get(
                token=token, 
                is_used=False, 
                expires_at__gt=timezone.now()
            )
            
            # Validácia hesla
            is_valid, message = SecurityService.validate_password(new_password)
            if not is_valid:
                raise ValueError(message)
            
            # Aktualizácia hesla
            user = reset_token.user
            user.password = make_password(new_password)
            user.save()
            
            # Označenie tokenu ako použitého
            reset_token.is_used = True
            reset_token.save()
            
            return True
        except PasswordResetToken.DoesNotExist:
            raise ValueError("Neplatný alebo expirovaný token")

class TwoFactorService:
    """
    Servisná trieda pre dvojfaktorovú autentifikáciu
    """
    @staticmethod
    def enable_two_factor(user):
        """
        Aktivácia dvojfaktorovej autentifikácie
        """
        # Generovanie secret key pre TOTP
        secret_key = pyotp.random_base32()
        
        # Vygenerovanie záložných kódov
        backup_codes = [
            secrets.token_urlsafe(8) for _ in range(5)
        ]
        
        # Vytvorenie/aktualizácia záznamu
        two_factor, created = TwoFactorAuthentication.objects.get_or_create(
            user=user,
            defaults={
                'is_enabled': True,
                'secret_key': secret_key,
                'backup_codes': backup_codes
            }
        )
        
        if not created:
            two_factor.is_enabled = True
            two_factor.secret_key = secret_key
            two_factor.backup_codes = backup_codes
            two_factor.save()
        
        return {
            'secret_key': secret_key,
            'backup_codes': backup_codes
        }

    @staticmethod
    def disable_two_factor(user):
        """
        Deaktivácia dvojfaktorovej autentifikácie
        """
        try:
            two_factor = TwoFactorAuthentication.objects.get(user=user)
            two_factor.is_enabled = False
            two_factor.save()
            return True
        except TwoFactorAuthentication.DoesNotExist:
            return False

    @staticmethod
    def verify_two_factor(user, code):
        """
        Overenie dvojfaktorového kódu
        """
        try:
            two_factor = TwoFactorAuthentication.objects.get(
                user=user, 
                is_enabled=True
            )
            
            # Overenie TOTP kódu
            totp = pyotp.TOTP(two_factor.secret_key)
            if totp.verify(code):
                return True
            
            # Overenie záložných kódov
            if code in two_factor.backup_codes:
                # Odstránenie použitého záložného kódu
                two_factor.backup_codes.remove(code)
                two_factor.save()
                return True
            
            return False
        except TwoFactorAuthentication.DoesNotExist:
            return False