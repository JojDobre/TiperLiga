from django.db import models
from django.utils import timezone
from django.conf import settings

class UserActivityLog(models.Model):
    """
    Model pre zaznamenávanie aktivít užívateľa
    """
    ACTIVITY_TYPES = (
        ('login', 'Prihlásenie'),
        ('logout', 'Odhlásenie'),
        ('bet_placed', 'Tip umiestnený'),
        ('profile_update', 'Aktualizácia profilu'),
        ('password_change', 'Zmena hesla'),
        ('friend_request', 'Žiadosť o priateľstvo'),
        ('challenge_created', 'Výzva vytvorená'),
        ('competition_joined', 'Súťaž pripojená')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    additional_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Aktivita užívateľa'
        verbose_name_plural = 'Aktivity užívateľov'

class UserDeviceInfo(models.Model):
    """
    Model pre sledovanie zariadení užívateľa
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    device_type = models.CharField(max_length=50)
    browser = models.CharField(max_length=100)
    os = models.CharField(max_length=100)
    last_login = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        unique_together = ('user', 'device_type', 'browser', 'os')

class UserActivityService:
    """
    Servisná trieda pre správu aktivít užívateľa
    """
    @staticmethod
    def log_activity(user, activity_type, additional_data=None, request=None):
        """
        Zaznamenanie aktivity užívateľa
        """
        # Extrakcia IP adresy a user agent
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = UserActivityService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Vytvorenie záznamu aktivity
        activity = UserActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {}
        )
        
        return activity

    @staticmethod
    def _get_client_ip(request):
        """
        Získanie IP adresy klienta
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def track_device(user, request):
        """
        Sledovanie zariadenia užívateľa
        """
        # Parsovanie user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_info = UserActivityService._parse_user_agent(user_agent)
        
        # Získanie IP adresy
        ip_address = UserActivityService._get_client_ip(request)
        
        # Vytvorenie/aktualizácia záznamu zariadenia
        device, created = UserDeviceInfo.objects.get_or_create(
            user=user,
            device_type=device_info['device_type'],
            browser=device_info['browser'],
            os=device_info['os'],
            defaults={
                'last_login': timezone.now(),
                'ip_address': ip_address,
                'is_active': True
            }
        )
        
        # Aktualizácia existujúceho zariadenia
        if not created:
            device.last_login = timezone.now()
            device.ip_address = ip_address
            device.is_active = True
            device.save()
        
        return device

    @staticmethod
    def _parse_user_agent(user_agent):
        """
        Parsovanie user agent reťazca
        """
        # Zjednodušená implementácia, pre produkciu odporúčam použiť knižnicu
        import re

        # Detekcia zariadenia
        device_type = 'desktop'
        if 'Mobile' in user_agent:
            device_type = 'mobile'
        elif 'Tablet' in user_agent:
            device_type = 'tablet'

        # Detekcia prehliadača
        browser = 'unknown'
        if 'Chrome' in user_agent:
            browser = 'Chrome'
        elif 'Firefox' in user_agent:
            browser = 'Firefox'
        elif 'Safari' in user_agent:
            browser = 'Safari'
        elif 'MSIE' in user_agent or 'Trident' in user_agent:
            browser = 'Internet Explorer'

        # Detekcia operačného systému
        os = 'unknown'
        if 'Windows' in user_agent:
            os = 'Windows'
        elif 'Macintosh' in user_agent:
            os = 'macOS'
        elif 'Linux' in user_agent:
            os = 'Linux'
        elif 'Android' in user_agent:
            os = 'Android'
        elif 'iOS' in user_agent:
            os = 'iOS'

        return {
            'device_type': device_type,
            'browser': browser,
            'os': os
        }

class UserSecurityAnalytics:
    """
    Analytická trieda pre bezpečnostné štatistiky
    """
    @staticmethod
    def get_recent_activities(user, days=30):
        """
        Získanie nedávnych aktivít užívateľa
        """
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        return UserActivityLog.objects.filter(
            user=user, 
            timestamp__gte=start_date
        )

    @staticmethod
    def detect_suspicious_activities(user):
        """
        Detekcia podozrivých aktivít
        """
        # Príklady podozrivých aktivít
        suspicious_activities = []
        
        # Viacnásobné neúspešné prihlásenia
        failed_logins = UserActivityLog.objects.filter(
            user=user,
            activity_type='login_failed'
        ).count()
        
        if failed_logins > 5:
            suspicious_activities.append({
                'type': 'multiple_failed_logins',
                'count': failed_logins
            })
        
        # Prihlásenia z neznámych zariadení
        devices = UserDeviceInfo.objects.filter(user=user)
        if devices.count() > 3:
            suspicious_activities.append({
                'type': 'multiple_devices',
                'device_count': devices.count()
            })
        
        return suspicious_activities