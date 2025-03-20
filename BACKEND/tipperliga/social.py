from django.db import models
from django.db.models import Q
from .models import CustomUser

class FriendRequest(models.Model):
    """
    Model pre žiadosti o priateľstvo
    """
    STATUS_CHOICES = (
        ('pending', 'Čaká na schválenie'),
        ('accepted', 'Schválené'),
        ('rejected', 'Zamietnuté')
    )

    sender = models.ForeignKey(CustomUser, related_name='sent_friend_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(CustomUser, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')

class Friendship(models.Model):
    """
    Model priateľských vzťahov
    """
    user1 = models.ForeignKey(CustomUser, related_name='friends_1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(CustomUser, related_name='friends_2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

class SocialInteractionLog(models.Model):
    """
    Záznam sociálnych interakcií
    """
    INTERACTION_TYPES = (
        ('friend_request_sent', 'Odoslaná žiadosť o priateľstvo'),
        ('friend_request_accepted', 'Prijatá žiadosť o priateľstvo'),
        ('friend_request_rejected', 'Zamietnutá žiadosť o priateľstvo'),
        ('message_sent', 'Správa odoslaná'),
        ('bet_challenge', 'Výzva na stávku')
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=50, choices=INTERACTION_TYPES)
    target_user = models.ForeignKey(CustomUser, related_name='interactions_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    additional_data = models.JSONField(null=True, blank=True)

class SocialService:
    @staticmethod
    def send_friend_request(sender, receiver):
        """
        Odoslanie žiadosti o priateľstvo
        """
        # Kontrola existujúcich požiadaviek
        existing_request = FriendRequest.objects.filter(
            Q(sender=sender, receiver=receiver) | 
            Q(sender=receiver, receiver=sender)
        ).first()

        if existing_request:
            if existing_request.status == 'pending':
                raise ValueError("Žiadosť o priateľstvo už existuje")
            if existing_request.status == 'accepted':
                raise ValueError("Užívatelia sú už priatelia")

        # Vytvorenie novej žiadosti
        friend_request = FriendRequest.objects.create(
            sender=sender,
            receiver=receiver,
            status='pending'
        )

        # Zaznamenanie interakcie
        SocialInteractionLog.objects.create(
            user=sender,
            interaction_type='friend_request_sent',
            target_user=receiver
        )

        return friend_request

    @staticmethod
    def accept_friend_request(request_id, receiver):
        """
        Prijatie žiadosti o priateľstvo
        """
        try:
            friend_request = FriendRequest.objects.get(
                id=request_id, 
                receiver=receiver, 
                status='pending'
            )

            # Aktualizácia statusu
            friend_request.status = 'accepted'
            friend_request.save()

            # Vytvorenie priateľstva
            Friendship.objects.create(
                user1=friend_request.sender,
                user2=friend_request.receiver
            )

            # Zaznamenanie interakcie
            SocialInteractionLog.objects.create(
                user=receiver,
                interaction_type='friend_request_accepted',
                target_user=friend_request.sender
            )

            return friend_request
        except FriendRequest.DoesNotExist:
            raise ValueError("Žiadosť o priateľstvo nebola nájdená")

    @staticmethod
    def reject_friend_request(request_id, receiver):
        """
        Zamietnutie žiadosti o priateľstvo
        """
        try:
            friend_request = FriendRequest.objects.get(
                id=request_id, 
                receiver=receiver, 
                status='pending'
            )

            # Aktualizácia statusu
            friend_request.status = 'rejected'
            friend_request.save()

            # Zaznamenanie interakcie
            SocialInteractionLog.objects.create(
                user=receiver,
                interaction_type='friend_request_rejected',
                target_user=friend_request.sender
            )

            return friend_request
        except FriendRequest.DoesNotExist:
            raise ValueError("Žiadosť o priateľstvo nebola nájdená")

    @staticmethod
    def get_friends(user):
        """
        Získanie zoznamu priateľov užívateľa
        """
        friends_1 = Friendship.objects.filter(user1=user).values_list('user2', flat=True)
        friends_2 = Friendship.objects.filter(user2=user).values_list('user1', flat=True)
        
        friend_ids = list(set(list(friends_1) + list(friends_2)))
        return CustomUser.objects.filter(id__in=friend_ids)

    @staticmethod
    def remove_friend(user, friend_to_remove):
        """
        Odstránenie priateľa
        """
        try:
            friendship = Friendship.objects.get(
                Q(user1=user, user2=friend_to_remove) | 
                Q(user1=friend_to_remove, user2=user)
            )
            friendship.delete()
            return True
        except Friendship.DoesNotExist:
            return False