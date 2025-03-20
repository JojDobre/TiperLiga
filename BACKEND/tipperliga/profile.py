from django.db import models
from django.core.validators import FileExtensionValidator
from .models import CustomUser

class UserProfile(models.Model):
    """
    Rozšírený profil užívateľa
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Základné informácie
    display_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Nastavenia súkromia
    show_full_name = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    
    # Avatар
    avatar = models.ImageField(
        upload_to='avatars/', 
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        null=True, 
        blank=True
    )
    
    # Sociálne prepojenia
    twitter_handle = models.CharField(max_length=50, blank=True)
    facebook_link = models.URLField(blank=True)
    
    # Notifikačné preferencie
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    
    # Preferovaný šport/liga
    preferred_sport = models.CharField(max_length=100, blank=True)
    preferred_leagues = models.ManyToManyField('League', blank=True)
    
    # Štatistiky profilu
    total_bets = models.IntegerField(default=0)
    total_correct_bets = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
    
    @property
    def accuracy_percentage(self):
        """
        Výpočet presnosti tipov
        """
        if self.total_bets == 0:
            return 0
        return (self.total_correct_bets / self.total_bets) * 100

class UserSettings(models.Model):
    """
    Užívateľské nastavenia
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='settings')
    
    # Téma rozhrania
    THEME_CHOICES = [
        ('light', 'Svetlá'),
        ('dark', 'Tmavá'),
        ('system', 'Systémová')
    ]
    interface_theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    
    # Jazyk
    LANGUAGE_CHOICES = [
        ('sk', 'Slovenčina'),
        ('en', 'Angličtina'),
        ('cz', 'Čeština')
    ]
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='sk')
    
    # Notifikačné nastavenia
    notification_frequency = models.CharField(
        max_length=20, 
        choices=[
            ('immediate', 'Okamžité'),
            ('daily', 'Denne'),
            ('weekly', 'Týždenne')
        ], 
        default='daily'
    )
    
    # Súkromie
    profile_visibility = models.CharField(
        max_length=20, 
        choices=[
            ('public', 'Verejný'),
            ('friends', 'Len priatelia'),
            ('private', 'Súkromný')
        ], 
        default='public'
    )
    
    # Ďalšie nastavenia
    show_betting_history = models.BooleanField(default=True)
    allow_friend_requests = models.BooleanField(default=True)

class ProfileService:
    @staticmethod
    def create_user_profile(user):
        """
        Automatické vytvorenie profilu a nastavení pre nového užívateľa
        """
        UserProfile.objects.create(user=user)
        UserSettings.objects.create(user=user)

    @staticmethod
    def update_profile(user, profile_data, settings_data=None):
        """
        Aktualizácia profilu a nastavení užívateľa
        """
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # Aktualizácia profilu
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        
        # Aktualizácia nastavení, ak sú poskytnuté
        if settings_data:
            settings, _ = UserSettings.objects.get_or_create(user=user)
            for key, value in settings_data.items():
                setattr(settings, key, value)
            settings.save()
        
        return profile

    @staticmethod
    def get_user_profile_details(user):
        """
        Komplexné načítanie detailov profilu
        """
        profile = UserProfile.objects.get(user=user)
        settings = UserSettings.objects.get(user=user)
        
        return {
            'profile': {
                'display_name': profile.display_name,
                'bio': profile.bio,
                'avatar': profile.avatar.url if profile.avatar else None,
                'total_bets': profile.total_bets,
                'accuracy_percentage': profile.accuracy_percentage
            },
            'settings': {
                'theme': settings.interface_theme,
                'language': settings.language,
                'notification_frequency': settings.notification_frequency,
                'profile_visibility': settings.profile_visibility
            }
        }