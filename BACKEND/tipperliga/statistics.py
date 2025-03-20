from django.db.models import Count, Avg, Sum
from django.db.models.functions import TruncMonth
from .models import Bet, Match, CustomUser, League
from django.db import models  # Pridaj tento import na začiatok súboru


class StatisticsService:
    @staticmethod
    def get_user_overall_statistics(user):
        """
        Komplexné štatistiky pre užívateľa
        """
        total_bets = Bet.objects.filter(user=user)
        
        return {
            'total_bets': total_bets.count(),
            'correct_bets_percentage': StatisticsService.calculate_correct_bets_percentage(user),
            'total_points': total_bets.aggregate(Sum('points_earned'))['points_earned__sum'] or 0,
            'average_points_per_bet': total_bets.aggregate(Avg('points_earned'))['points_earned__avg'] or 0,
            'best_month': StatisticsService.get_best_betting_month(user)
        }

    @staticmethod
    def calculate_correct_bets_percentage(user):
        """
        Výpočet percentuálnej úspešnosti tipov
        """
        total_bets = Bet.objects.filter(user=user).count()
        correct_bets = Bet.objects.filter(user=user, points_earned__gt=0).count()
        
        return (correct_bets / total_bets * 100) if total_bets > 0 else 0

    @staticmethod
    def get_best_betting_month(user):
        """
        Nájdenie mesiaca s najvyššími bodmi
        """
        monthly_stats = Bet.objects.filter(user=user)\
            .annotate(month=TruncMonth('match__match_date'))\
            .values('month')\
            .annotate(total_points=Sum('points_earned'))\
            .order_by('-total_points')\
            .first()
        
        return monthly_stats

    @staticmethod
    def generate_league_report(league):
        """
        Generovanie komplexného reportu pre ligu
        """
        participants = CustomUser.objects.filter(bet__match__round__competition__leagues=league).distinct()
        
        league_report = {
            'total_participants': participants.count(),
            'top_performers': StatisticsService.get_top_performers(league, 10),
            'participation_trends': StatisticsService.get_participation_trends(league),
            'bet_distribution': StatisticsService.get_bet_distribution(league)
        }
        
        return league_report

    @staticmethod
    def get_top_performers(league, limit=10):
        """
        Top performing užívatelia v lige
        """
        top_users = CustomUser.objects.filter(
            bet__match__round__competition__leagues=league
        ).annotate(
            total_points=Sum('bet__points_earned')
        ).order_by('-total_points')[:limit]
        
        return [
            {
                'username': user.username,
                'total_points': user.total_points,
                'rank': index + 1
            } for index, user in enumerate(top_users)
        ]

    @staticmethod
    def get_participation_trends(league):
        """
        Trendy participácie v lige
        """
        participation_by_month = Bet.objects.filter(
            match__round__competition__leagues=league
        ).annotate(
            month=TruncMonth('match__match_date')
        ).values('month').annotate(
            total_bets=Count('id'),
            total_points=Sum('points_earned')
        ).order_by('month')
        
        return list(participation_by_month)

    @staticmethod
    def get_bet_distribution(league):
        """
        Distribúcia tipov podľa výsledkov
        """
        bets = Bet.objects.filter(
            match__round__competition__leagues=league
        )
        
        return {
            'total_bets': bets.count(),
            'correct_bets': bets.filter(points_earned__gt=0).count(),
            'perfect_bets': bets.filter(points_earned=10).count(),
            'distribution_by_points': list(
                bets.values('points_earned')
                .annotate(count=Count('id'))
                .order_by('points_earned')
            )
        }

class ReportGenerator:
    @staticmethod
    def generate_periodic_report(league, report_type='monthly'):
        """
        Generovanie periodických reportov
        """
        report_data = StatisticsService.generate_league_report(league)
        
        # Uloženie reportu do databázy alebo odoslanie emailom
        report = LeagueReport.objects.create(
            league=league,
            report_type=report_type,
            data=report_data
        )
        
        return report

class LeagueReport(models.Model):
    """
    Model pre ukladanie vygenerovaných reportov
    """
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']