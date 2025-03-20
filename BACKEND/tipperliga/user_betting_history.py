from django.db import models
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from .models import CustomUser, Bet, Match, Competition, League
from .user_analytics import UserBettingTrend

class UserBettingHistoryEntry(models.Model):
    """
    Model pre detailný záznam histórie tipov
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    bet = models.ForeignKey(Bet, on_delete=models.CASCADE)
    
    home_score_prediction = models.IntegerField()
    away_score_prediction = models.IntegerField()
    actual_home_score = models.IntegerField()
    actual_away_score = models.IntegerField()
    
    points_earned = models.IntegerField(default=0)
    is_correct = models.BooleanField(default=False)
    
    bet_date = models.DateTimeField(auto_now_add=True)
    match_date = models.DateTimeField()
    
    class Meta:
        ordering = ['-match_date']
        unique_together = ('user', 'match')

class UserBettingHistoryService:
    """
    Servisná trieda pre správu histórie tipov
    """
    @staticmethod
    def create_history_entry(bet):
        """
        Vytvorenie záznamu histórie tipu
        """
        history_entry = UserBettingHistoryEntry.objects.create(
            user=bet.user,
            match=bet.match,
            bet=bet,
            home_score_prediction=bet.home_score_prediction,
            away_score_prediction=bet.away_score_prediction,
            actual_home_score=bet.match.home_score or 0,
            actual_away_score=bet.match.away_score or 0,
            points_earned=bet.points_earned,
            is_correct=bet.points_earned > 0,
            match_date=bet.match.match_date
        )
        
        return history_entry

    @staticmethod
    def get_user_betting_history(user, filters=None):
        """
        Získanie histórie tipov s možnosťou filtrácie
        
        Príklad filtrov:
        filters = {
            'competition_id': 1,
            'league_id': 2,
            'date_from': date,
            'date_to': date,
            'is_correct': True
        }
        """
        history_entries = UserBettingHistoryEntry.objects.filter(user=user)
        
        if filters:
            # Filtrovanie podľa súťaže
            if filters.get('competition_id'):
                history_entries = history_entries.filter(
                    match__round__competition_id=filters['competition_id']
                )
            
            # Filtrovanie podľa ligy
            if filters.get('league_id'):
                history_entries = history_entries.filter(
                    match__round__competition__leagues__id=filters['league_id']
                )
            
            # Filtrovanie podľa dátumu
            if filters.get('date_from'):
                history_entries = history_entries.filter(
                    match_date__gte=filters['date_from']
                )
            
            if filters.get('date_to'):
                history_entries = history_entries.filter(
                    match_date__lte=filters['date_to']
                )
            
            # Filtrovanie podľa správnosti tipu
            if 'is_correct' in filters:
                history_entries = history_entries.filter(
                    is_correct=filters['is_correct']
                )
        
        return history_entries

    @staticmethod
    def get_user_betting_summary(user, period_days=30):
        """
        Súhrn tipovacích aktivít za dané obdobie
        """
        start_date = timezone.now() - timezone.timedelta(days=period_days)
        
        history_entries = UserBettingHistoryEntry.objects.filter(
            user=user,
            match_date__gte=start_date
        )
        
        summary = {
            'total_bets': history_entries.count(),
            'correct_bets': history_entries.filter(is_correct=True).count(),
            'total_points_earned': history_entries.aggregate(
                total_points=Sum('points_earned')
            )['total_points'] or 0,
            'accuracy_percentage': (
                history_entries.filter(is_correct=True).count() / 
                history_entries.count() * 100 if history_entries.count() > 0 else 0
            ),
            'performance_by_competition': list(
                history_entries.values('match__round__competition__name')
                .annotate(
                    total_bets=Count('id'),
                    correct_bets=Count('id', filter=Q(is_correct=True)),
                    total_points=Sum('points_earned')
                )
            )
        }
        
        return summary


class UserBettingTrendService:
    """
    Servisná trieda pre sledovanie trendov tipov
    """
    @staticmethod
    def update_daily_trends(user, date=None):
        """
        Aktualizácia denných trendov
        """
        if not date:
            date = timezone.now().date()
        
        # Výpočet denných štatistík
        daily_entries = UserBettingHistoryEntry.objects.filter(
            user=user, 
            match_date__date=date
        )
        
        trend, created = UserBettingTrend.objects.get_or_create(
            user=user,
            date=date
        )
        
        trend.total_bets = daily_entries.count()
        trend.correct_bets = daily_entries.filter(is_correct=True).count()
        trend.total_points = daily_entries.aggregate(
            total_points=Sum('points_earned')
        )['total_points'] or 0
        
        trend.save()
        return trend

    @staticmethod
    def get_user_betting_trends(user, period_days=30):
        """
        Získanie trendov tipov za dané obdobie
        """
        start_date = timezone.now().date() - timezone.timedelta(days=period_days)
        
        trends = UserBettingTrend.objects.filter(
            user=user,
            date__gte=start_date
        )
        
        return trends