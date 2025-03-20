from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from .profile import ProfileService

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatické vytvorenie profilu pri registrácii
    """
    if created:
        ProfileService.create_user_profile(instance)