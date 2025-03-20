from django.db import models
from django.conf import settings
from django.utils import timezone
from fcm_django.models import FCMDevice
from firebase_admin import messaging

class NotificationType(models.Model):
    """
    Definícia typov notifikácií
    """
    CATEGORY_CHOICES = (
        ('bet', 'Tipovanie'),
        ('league', 'Liga'),
        ('friend', 'Priatelia'),
        ('system', 'Systémové')
    )

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class UserNotificationPreference(models.Model):
    """
    Nastavenia notifikácií pre užívateľa
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    
    # Kanály notifikácií
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'notification_type')

class Notification(models.Model):
    """
    Model pre ukladanie notifikácií
    """
    STATUS_CHOICES = (
        ('unread', 'Neprečítané'),
        ('read', 'Prečítané'),
        ('archived', 'Archivované')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notification_type = models.ForeignKey(NotificationType, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Voliteľné prepojenie na špecifickú entitu
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

class NotificationService:
    """
    Servisná trieda pre správu notifikácií
    """
    @staticmethod
    def create_notification(user, title, message, notification_type=None, related_object=None):
        """
        Vytvorenie notifikácie pre užívateľa
        """
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_id=related_object.id if related_object else None,
            related_object_type=related_object.__class__.__name__ if related_object else None
        )
        
        return notification

    @staticmethod
    def send_push_notification(user, title, message, data=None):
        """
        Odoslanie push notifikácie cez Firebase Cloud Messaging
        """
        try:
            # Získanie všetkých zariadení užívateľa
            devices = FCMDevice.objects.filter(user=user)
            
            if not devices.exists():
                return False
            
            # Príprava správy
            push_message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=message
                ),
                data=data or {},
                tokens=[device.registration_token for device in devices]
            )
            
            # Odoslanie správy
            response = messaging.send_multicast(push_message)
            
            return response.success_count > 0
        except Exception as e:
            # Logovanie chyby
            print(f"Push notification error: {e}")
            return False

    @staticmethod
    def send_email_notification(user, subject, message):
        """
        Odoslanie emailovej notifikácie
        """
        from django.core.mail import send_mail
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Logovanie chyby
            print(f"Email notification error: {e}")
            return False

class NotificationTriggerService:
    """
    Servisná trieda pre automatické spúšťanie notifikácií
    """
    @staticmethod
    def trigger_bet_notifications(bet):
        """
        Notifikácie súvisiace s tipovaním
        """
        user = bet.user
        match = bet.match
        
        # Notifikácia o umiestnení tipu
        notification_type, _ = NotificationType.objects.get_or_create(
            name='bet_placed', 
            category='bet'
        )
        
        notification = NotificationService.create_notification(
            user,
            'Tip bol umiestnený',
            f'Váš tip na zápas {match} bol zaznamenaný.',
            notification_type,
            bet
        )
        
        # Kontrola preferencií užívateľa
        preferences = UserNotificationPreference.objects.filter(
            user=user, 
            notification_type=notification_type
        ).first()
        
        # Odoslanie push notifikácie
        if preferences and preferences.push_enabled:
            NotificationService.send_push_notification(
                user,
                'Tip bol umiestnený',
                f'Váš tip na zápas {match} bol zaznamenaný.'
            )
        
        # Odoslanie emailu
        if preferences and preferences.email_enabled:
            NotificationService.send_email_notification(
                user,
                'Tip bol umiestnený',
                f'Váš tip na zápas {match} bol zaznamenaný.'
            )

    @staticmethod
    def trigger_league_notifications(league, event_type):
        """
        Notifikácie súvisiace s ligou
        """
        # Notifikácie pre všetkých užívateľov v lige
        notification_type, _ = NotificationType.objects.get_or_create(
            name=f'league_{event_type}', 
            category='league'
        )
        
        # Rôzne typy udalostí v lige
        event_messages = {
            'round_started': 'Začalo nové kolo v lige',
            'round_ended': 'Kolo v lige bolo ukončené',
            'leaderboard_updated': 'Rebríček ligy bol aktualizovaný'
        }
        
        # Nájdenie užívateľov v lige
        users = league.created_by.customuser_set.all()
        
        for user in users:
            # Vytvorenie notifikácie
            notification = NotificationService.create_notification(
                user,
                f'Udalosť v lige {league.name}',
                event_messages.get(event_type, 'Nastala udalosť v lige'),
                notification_type,
                league
            )
            
            # Kontrola preferencií užívateľa
            preferences = UserNotificationPreference.objects.filter(
                user=user, 
                notification_type=notification_type
            ).first()
            
            # Odoslanie push notifikácie
            if preferences and preferences.push_enabled:
                NotificationService.send_push_notification(
                    user,
                    f'Udalosť v lige {league.name}',
                    event_messages.get(event_type, 'Nastala udalosť v lige')
                )