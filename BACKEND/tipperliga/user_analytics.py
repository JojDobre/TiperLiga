from django.db import models
from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, Bet, Match, Competition, League

class UserBettingProfile:
    """
    Komplexný profil tipovacích aktivít užívateľa
    """
    @staticmethod
    def get_overall_betting_statistics(user):
        """
        Celkové štatistiky tipov užívateľa
        """
        total_bets = Bet.objects.filter(user=user)
        
        return {
            'total_bets': total_bets.count(),
            'correct_bets': total_bets.filter(points_earned__gt=0).count(),
            'accuracy_percentage': UserBettingProfile._calculate_accuracy(user),
            'total_points_earned': total_bets.aggregate(Sum('points_earned'))['points_earned__sum'] or 0,
            'average_points_per_bet': total_bets.aggregate(Avg('points_earned'))['points_earned__avg'] or 0
        }

    @staticmethod
    def _calculate_accuracy(user):
        """
        Výpočet presnosti tipov
        """
        total_bets = Bet.objects.filter(user=user).count()
        correct_bets = Bet.objects.filter(user=user, points_earned__gt=0).count()
        
        return (correct_bets / total_bets * 100) if total_bets > 0 else 0

    @staticmethod
    def get_betting_trends(user, period_days=30):
        """
        Trendy tipov za dané obdobie
        """
        start_date = timezone.now() - timedelta(days=period_days)
        
        # Denné štatistiky tipov
        daily_stats = Bet.objects.filter(
            user=user, 
            match__match_date__gte=start_date
        ).annotate(
            bet_date=F('match__match_date')
        ).values('bet_date').annotate(
            total_bets=Count('id'),
            total_points=Sum('points_earned')
        ).order_by('bet_date')
        
        return list(daily_stats)

    @staticmethod
    def get_performance_by_competition(user):
        """
        Výkonnosť užívateľa podľa súťaží
        """
        competition_performance = Bet.objects.filter(user=user).values(
            'match__round__competition__name'
        ).annotate(
            total_bets=Count('id'),
            total_points=Sum('points_earned'),
            accuracy=Count(
                'id', 
                filter=Q(points_earned__gt=0)
            ) * 100.0 / Count('id')
        ).order_by('-total_points')
        
        return list(competition_performance)

    @staticmethod
    def get_most_successful_teams(user):
        """
        Najúspešnejšie tímy pre užívateľa
        """
        team_performance = Bet.objects.filter(user=user).values(
            'match__home_team__name', 
            'match__away_team__name'
        ).annotate(
            total_bets=Count('id'),
            total_points=Sum('points_earned'),
            accuracy=Count(
                'id', 
                filter=Q(points_earned__gt=0)
            ) * 100.0 / Count('id')
        ).order_by('-total_points')
        
        return list(team_performance)

class UserBettingTrend(models.Model):
    """
    Model pre ukladanie trendov tipov
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    total_bets = models.IntegerField(default=0)
    correct_bets = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

class UserBettingTrendService:
    """
    Servisná trieda pre sledovanie a ukladanie trendov
    """
    @staticmethod
    def update_daily_trends():
        """
        Denná aktualizácia trendov pre všetkých užívateľov
        """
        users = CustomUser.objects.all()
        today = timezone.now().date()
        
        for user in users:
            # Výpočet denných štatistík
            daily_bets = Bet.objects.filter(
                user=user, 
                match__match_date__date=today
            )
            
            trend, created = UserBettingTrend.objects.get_or_create(
                user=user,
                date=today
            )
            
            trend.total_bets = daily_bets.count()
            trend.correct_bets = daily_bets.filter(points_earned__gt=0).count()
            trend.total_points = daily_bets.aggregate(Sum('points_earned'))['points_earned__sum'] or 0
            
            trend.save()

class UserLeaguePerformance(models.Model):
    """
    Model pre výkonnosť užívateľa v jednotlivých ligách
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    total_bets = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'league')
        ordering = ['-total_points']

class UserLeaguePerformanceService:
    """
    Servisná trieda pre sledovanie výkonnosti v ligách
    """
    @staticmethod
    def update_league_performance(league):
        """
        Aktualizácia výkonnosti užívateľov v lige
        """
        # Získanie všetkých užívateľov, ktorí tipovali v danej lige
        users_in_league = CustomUser.objects.filter(
            bet__match__round__competition__leagues=league
        ).distinct()
        
        for user in users_in_league:
            # Výpočet celkových štatistík pre užívateľa v lige
            user_league_bets = Bet.objects.filter(
                user=user,
                match__round__competition__leagues=league
            )
            
            performance, created = UserLeaguePerformance.objects.get_or_create(
                user=user,
                league=league
            )
            
            performance.total_bets = user_league_bets.count()
            performance.total_points = user_league_bets.aggregate(Sum('points_earned'))['points_earned__sum'] or 0
            
            performance.save()
        
        # Aktualizácia poradia
        league_performances = UserLeaguePerformance.objects.filter(league=league).order_by('-total_points')
        
        for index, performance in enumerate(league_performances, 1):
            performance.rank = index
            performance.save()