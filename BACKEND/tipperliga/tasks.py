from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import *
from .scoring import LeagueScoring
from .team_management import TeamManager
from .achievements import AchievementService
from .competition_management import CompetitionManager
from .user_analytics import UserBettingProfile, UserBettingTrendService, UserLeaguePerformanceService
from .user_betting_history import (
    UserBettingHistoryService, 
    UserBettingTrendService
)
from .authentication import CustomUser
from .profile import ProfileService, UserProfile


@shared_task
def process_league_scoring():
    """
    Periodická úloha pre vyhodnotenie líg
    """
    leagues = League.objects.all()
    for league in leagues:
        LeagueScoring.update_user_points(league)

@shared_task
def generate_league_leaderboards():
    """
    Generovanie rebríčkov pre všetky ligy
    """
    leagues = League.objects.all()
    leaderboards = {}
    
    for league in leagues:
        leaderboards[league.id] = LeagueScoring.get_league_leaderboard(league)
    
    return leaderboards



from celery import shared_task
from .models import League
from .statistics import ReportGenerator

@shared_task
def generate_periodic_league_reports():
    """
    Periodické generovanie reportov pre všetky ligy
    """
    leagues = League.objects.all()
    
    reports = []
    for league in leagues:
        report = ReportGenerator.generate_periodic_report(league)
        reports.append({
            'league_id': league.id,
            'report_id': report.id
        })
    
    return reports


@shared_task
def process_achievements():
    """
    Periodické spracovanie achievementov pre všetkých užívateľov
    """
    users = CustomUser.objects.all()
    
    for user in users:
        AchievementService.check_and_award_achievements(user)

@shared_task
def update_competition_statuses():
    """
    Periodická aktualizácia stavov súťaží
    """
    competitions = Competition.objects.all()
    
    for competition in competitions:
        CompetitionManager.update_competition_status(competition)

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from .profile import ProfileService

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatické vytvorenie profilu pri registrácii
    """
    if created:
        # Overenie, či profil už neexistuje
        from .profile import UserProfile
        UserProfile.objects.get_or_create(user=instance)

def update_team_statistics():
    """
    Aktualizácia štatistík tímov po zápasoch
    """
    # Nájdenie všetkých zápasov s výsledkom za posledných 24 hodín
    recent_matches = Match.objects.filter(
        home_score__isnull=False, 
        match_date__gte=timezone.now() - timezone.timedelta(days=1)
    )
    
    for match in recent_matches:
        # Aktualizácia štatistík pre domáci tím
        TeamManager.update_team_statistics(match.home_team, match)
        
        # Aktualizácia štatistík pre hostujúci tím
        TeamManager.update_team_statistics(match.away_team, match)

@shared_task
def update_user_betting_trends():
    """
    Denná aktualizácia trendov tipov
    """
    UserBettingTrendService.update_daily_trends()

@shared_task
def update_league_performances():
    """
    Aktualizácia výkonnosti užívateľov v ligách
    """
    leagues = League.objects.all()
    
    for league in leagues:
        UserLeaguePerformanceService.update_league_performance(league)

@shared_task
def update_user_betting_history():
    """
    Aktualizácia histórie tipov pre všetkých užívateľov
    """
    # Nájdenie všetkýchbet záznamov za posledných 24 hodín
    recent_bets = Bet.objects.filter(
        match__home_score__isnull=False,
        match__match_date__gte=timezone.now() - timezone.timedelta(days=1)
    )
    
    for bet in recent_bets:
        # Vytvorenie záznamu histórie
        UserBettingHistoryService.create_history_entry(bet)


@shared_task
def update_daily_betting_trends():
    """
    Aktualizácia denných trendov pre všetkých užívateľov
    """
    users = CustomUser.objects.all()
    
    for user in users:
        UserBettingTrendService.update_daily_trends(user)