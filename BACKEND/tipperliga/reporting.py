from django.db import models
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from .models import CustomUser, Bet, Match, League, Competition, Team
from .notifications import NotificationService 
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


class ReportType(models.Model):
    """
    Definícia typov reportov
    """
    CATEGORY_CHOICES = (
        ('user', 'Užívateľské'),
        ('league', 'Liga'),
        ('competition', 'Súťaž'),
        ('system', 'Systémové')
    )

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Report(models.Model):
    """
    Model pre ukladanie vygenerovaných reportov
    """
    STATUS_CHOICES = (
        ('pending', 'Spracováva sa'),
        ('completed', 'Hotovo'),
        ('failed', 'Zlyhalo')
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_at = models.DateTimeField(auto_now_add=True)
    
    data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_at']

class ReportingService:
    """
    Servisná trieda pre generovanie reportov
    """
    @staticmethod
    def generate_user_betting_report(user, start_date=None, end_date=None):
        """
        Generovanie komplexného reportu pre užívateľa
        """
        # Nastavenie dátumového rozsahu
        if not start_date:
            start_date = timezone.now() - timezone.timedelta(days=30)
        if not end_date:
            end_date = timezone.now()

        # Základné štatistiky tipov
        bets = Bet.objects.filter(
            user=user, 
            match__match_date__range=[start_date, end_date]
        )

        report_data = {
            'total_bets': bets.count(),
            'correct_bets': bets.filter(points_earned__gt=0).count(),
            'total_points': bets.aggregate(Sum('points_earned'))['points_earned__sum'] or 0,
            'average_points_per_bet': bets.aggregate(Avg('points_earned'))['points_earned__avg'] or 0,
            
            # Štatistiky podľa súťaží
            'competition_performance': list(
                bets.values('match__round__competition__name')
                .annotate(
                    total_bets=Count('id'),
                    total_points=Sum('points_earned'),
                    accuracy=Count('id', filter=Q(points_earned__gt=0)) * 100.0 / Count('id')
                )
            ),
            
            # Najúspešnejšie tímy
            'most_successful_teams': list(
                bets.values('match__home_team__name', 'match__away_team__name')
                .annotate(
                    total_bets=Count('id'),
                    total_points=Sum('points_earned'),
                    accuracy=Count('id', filter=Q(points_earned__gt=0)) * 100.0 / Count('id')
                )
                .order_by('-total_points')[:10]
            )
        }

        return report_data

    @staticmethod
    def generate_league_performance_report(league, start_date=None, end_date=None):
        """
        Generovanie reportu pre ligu
        """
        # Nastavenie dátumového rozsahu
        if not start_date:
            start_date = timezone.now() - timezone.timedelta(days=30)
        if not end_date:
            end_date = timezone.now()

        # Štatistiky súťaží v lige
        competitions = league.competitions.filter(
            start_date__lte=end_date, 
            end_date__gte=start_date
        )

        report_data = {
            'league_name': league.name,
            'total_competitions': competitions.count(),
            
            # Top užívatelia v lige
            'top_users': list(
                Bet.objects.filter(
                    match__round__competition__in=competitions
                ).values('user__username')
                .annotate(
                    total_bets=Count('id'),
                    total_points=Sum('points_earned'),
                    accuracy=Count('id', filter=Q(points_earned__gt=0)) * 100.0 / Count('id')
                )
                .order_by('-total_points')[:10]
            ),
            
            # Štatistiky súťaží
            'competition_stats': list(
                competitions.annotate(
                    total_matches=Count('round__match'),
                    completed_matches=Count('round__match', filter=Q(round__match__home_score__isnull=False))
                )
            )
        }

        return report_data

    @staticmethod
    def generate_competition_report(competition, start_date=None, end_date=None):
        """
        Generovanie reportu pre súťaž
        """
        # Nastavenie dátumového rozsahu
        if not start_date:
            start_date = competition.start_date
        if not end_date:
            end_date = competition.end_date

        # Štatistiky zápasov
        matches = Match.objects.filter(
            round__competition=competition,
            match_date__range=[start_date, end_date]
        )

        report_data = {
            'competition_name': competition.name,
            'total_matches': matches.count(),
            
            # Štatistiky tímov
            'team_performance': list(
                matches.values('home_team__name', 'away_team__name')
                .annotate(
                    total_matches=Count('id'),
                    wins_home=Count('id', filter=Q(home_score__gt=F('away_score'))),
                    wins_away=Count('id', filter=Q(away_score__gt=F('home_score'))),
                    draws=Count('id', filter=Q(home_score=F('away_score'))),
                    goals_scored_home=Sum('home_score'),
                    goals_scored_away=Sum('away_score')
                )
            ),
            
            # Štatistiky tipov
            'betting_stats': {
                'total_bets': Bet.objects.filter(match__in=matches).count(),
                'correct_bets': Bet.objects.filter(
                    match__in=matches, 
                    points_earned__gt=0
                ).count(),
                'average_points_per_bet': Bet.objects.filter(
                    match__in=matches
                ).aggregate(Avg('points_earned'))['points_earned__avg'] or 0
            }
        }

        return report_data

class ReportGenerationService:
    """
    Servisná trieda pre asynchrónne generovanie reportov
    """
    @staticmethod
    def create_report(user, report_type, start_date=None, end_date=None, additional_params=None):
        """
        Vytvorenie a naplanovanie generovania reportu
        """
        # Vytvorenie záznamu reportu
        report = Report.objects.create(
            user=user,
            report_type=report_type,
            start_date=start_date or timezone.now() - timezone.timedelta(days=30),
            end_date=end_date or timezone.now(),
            status='pending'
        )

        # Asynchrónne generovanie reportu
        ReportGenerationService.generate_report_task.delay(
            report_id=report.id,
            additional_params=additional_params or {}
        )

        return report

    @staticmethod
    @shared_task
    def generate_report_task(report_id, additional_params=None):
        """
        Asynchrónna úloha pre generovanie reportu
        """
        try:
            report = Report.objects.get(id=report_id)
            
            # Výber typu reportu a generovania
            if report.report_type.category == 'user':
                report.data = ReportingService.generate_user_betting_report(
                    report.user, 
                    report.start_date, 
                    report.end_date
                )
            elif report.report_type.category == 'league':
                league_id = additional_params.get('league_id')
                league = League.objects.get(id=league_id)
                report.data = ReportingService.generate_league_performance_report(
                    league, 
                    report.start_date, 
                    report.end_date
                )
            elif report.report_type.category == 'competition':
                competition_id = additional_params.get('competition_id')
                competition = Competition.objects.get(id=competition_id)
                report.data = ReportingService.generate_competition_report(
                    competition, 
                    report.start_date, 
                    report.end_date
                )
            
            report.status = 'completed'
            report.save()
            
            # Voliteľné: Odoslanie notifikácie o dokončení reportu
            NotificationService.create_notification(
                report.user,
                'Report bol vygenerovaný',
                f'Report {report.report_type.name} bol úspešne vytvorený.',
                None,
                report
            )
        
        except Exception as e:
            report.status = 'failed'
            report.data = {'error': str(e)}
            report.save()
            
            # Logovanie chyby
            logger.error(f"Report generation failed: {e}")