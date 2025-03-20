from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Bet, Match, CustomUser, League

class BettingRules:
    """
    Centrálna trieda pre pravidlá a validácie tipov
    """
    @staticmethod
    def validate_bet(user, match, home_score, away_score):
        """
        Komplexná validácia tipu
        """
        # Kontrola existencie zápasu
        if not match:
            raise ValidationError("Zápas neexistuje")

        # Kontrola termínu uzávierky
        if timezone.now() > match.round.deadline:
            raise ValidationError("Tipovanie po termíne uzávierky nie je povolené")

        # Kontrola duplicitných tipov
        existing_bet = Bet.objects.filter(
            user=user, 
            match=match
        ).exists()

        if existing_bet:
            raise ValidationError("Na tento zápas ste už tipovali")

        # Validácia skóre (voliteľné pravidlá)
        if home_score < 0 or away_score < 0:
            raise ValidationError("Skóre nemôže byť záporné")

        # Ďalšie špecifické pravidlá môžu byť pridané podľa potreby
        return True

class BetService:
    """
    Servisná trieda pre správu tipov
    """
    @staticmethod
    def place_bet(user, match, home_score, away_score):
        """
        Umiestnenie tipu s komplexnou validáciou
        """
        # Validácia tipu
        BettingRules.validate_bet(user, match, home_score, away_score)

        # Vytvorenie tipu
        bet = Bet.objects.create(
            user=user,
            match=match,
            home_score_prediction=home_score,
            away_score_prediction=away_score
        )

        return bet

    @staticmethod
    def update_bet(bet, home_score, away_score):
        """
        Aktualizácia existujúceho tipu
        """
        # Kontrola možnosti zmeny tipu
        if timezone.now() > bet.match.round.deadline:
            raise ValidationError("Tip už nie je možné zmeniť")

        # Aktualizácia hodnôt
        bet.home_score_prediction = home_score
        bet.away_score_prediction = away_score
        bet.save()

        return bet

    @staticmethod
    def get_user_bets(user, league=None, competition=None):
        """
        Získanie tipov užívateľa s možnosťou filtrácie
        """
        bets = Bet.objects.filter(user=user)

        if league:
            bets = bets.filter(match__round__competition__leagues=league)

        if competition:
            bets = bets.filter(match__round__competition=competition)

        return bets

class BettingLimits:
    """
    Systém pre nastavenie limitov a obmedzení
    """
    @staticmethod
    def set_league_betting_limits(league, max_bets_per_round=None, max_points_per_round=None):
        """
        Nastavenie limitov pre ligu
        """
        league.max_bets_per_round = max_bets_per_round
        league.max_points_per_round = max_points_per_round
        league.save()

    @staticmethod
    def check_league_betting_limits(user, league, round):
        """
        Kontrola limitov pre ligu
        """
        # Kontrola maximálneho počtu tipov
        if league.max_bets_per_round:
            user_bets_count = Bet.objects.filter(
                user=user, 
                match__round=round
            ).count()

            if user_bets_count >= league.max_bets_per_round:
                raise ValidationError(f"Dosiahnutý maximálny počet tipov pre kolo: {league.max_bets_per_round}")

        # Kontrola maximálnych bodov
        if league.max_points_per_round:
            user_bets_points = Bet.objects.filter(
                user=user, 
                match__round=round
            ).aggregate(total_points=models.Sum('points_earned'))['total_points'] or 0

            if user_bets_points >= league.max_points_per_round:
                raise ValidationError(f"Dosiahnutý maximálny počet bodov pre kolo: {league.max_points_per_round}")

class BetChallengeSystem:
    """
    Systém pre výzvy medzi priateľmi
    """
    @staticmethod
    def create_bet_challenge(challenger, challenged_user, match, stake=None):
        """
        Vytvorenie výzvy na stávku
        """
        challenge = BetChallenge.objects.create(
            challenger=challenger,
            challenged_user=challenged_user,
            match=match,
            stake=stake,
            status='pending'
        )
        return challenge

    @staticmethod
    def accept_bet_challenge(challenge, home_score, away_score):
        """
        Prijatie výzvy na stávku
        """
        if challenge.status != 'pending':
            raise ValidationError("Výzva už bola spracovaná")

        challenge.challenged_user_prediction_home = home_score
        challenge.challenged_user_prediction_away = away_score
        challenge.status = 'accepted'
        challenge.save()

        return challenge

class BetChallenge(models.Model):
    """
    Model pre výzvy medzi priateľmi
    """
    STATUS_CHOICES = (
        ('pending', 'Čaká na schválenie'),
        ('accepted', 'Prijatá'),
        ('rejected', 'Zamietnutá'),
        ('completed', 'Ukončená')
    )

    challenger = models.ForeignKey(CustomUser, related_name='challenges_sent', on_delete=models.CASCADE)
    challenged_user = models.ForeignKey(CustomUser, related_name='challenges_received', on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    
    challenger_prediction_home = models.IntegerField()
    challenger_prediction_away = models.IntegerField()
    challenged_user_prediction_home = models.IntegerField(null=True, blank=True)
    challenged_user_prediction_away = models.IntegerField(null=True, blank=True)
    
    stake = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)