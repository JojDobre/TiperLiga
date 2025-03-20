from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, F  # Pro komplexní dotazy
from .models import Team, Match  # Import modelů

class PlayerTransfer(models.Model):
    """
    Model pre zaznamenávanie prestupov hráčov
    """
    player = models.ForeignKey('Player', on_delete=models.CASCADE)
    from_team = models.ForeignKey('Team', related_name='transfers_out', on_delete=models.CASCADE)
    to_team = models.ForeignKey('Team', related_name='transfers_in', on_delete=models.CASCADE)
    transfer_date = models.DateTimeField(auto_now_add=True)
    transfer_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.player} - {self.from_team} → {self.to_team}"

class TeamCategory(models.Model):
    """
    Kategorizácia tímov
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sport = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class TeamStatistics(models.Model):
    """
    Rozšírené štatistiky tímu
    """
    team = models.OneToOneField('Team', on_delete=models.CASCADE, related_name='statistics')
    total_matches = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    
    @property
    def win_percentage(self):
        return (self.wins / self.total_matches * 100) if self.total_matches > 0 else 0
    
    @property
    def goal_difference(self):
        return self.goals_scored - self.goals_conceded

class PlayerPosition(models.Model):
    """
    Pozície hráčov
    """
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10)
    sport = models.CharField(max_length=50, default='')

    def __str__(self):
        return self.name

class TeamManager:
    """
    Servisná trieda pre správu tímov
    """
    @staticmethod
    def create_team(
        name, 
        category, 
        country, 
        logo=None, 
        founded_date=None, 
        description=None
    ):
        """
        Vytvorenie nového tímu
        """
        # Validácia povinných polí
        if not name:
            raise ValidationError("Názov tímu je povinný")
        
        team = Team.objects.create(
            name=name,
            category=category,
            country=country,
            logo=logo,
            founded_date=founded_date,
            description=description
        )
        
        # Automatické vytvorenie štatistík tímu
        TeamStatistics.objects.create(team=team)
        
        return team
    @staticmethod
    def update_team_statistics(team, match):
        """
        Aktualizácia štatistík tímu po zápase
        """
        stats, created = TeamStatistics.objects.get_or_create(team=team)
        
        stats.total_matches += 1
        
        # Aktualizácia štatistík pre domáci tím
        if match.home_team == team:
            stats.goals_scored += match.home_score or 0
            stats.goals_conceded += match.away_score or 0
            
            if match.home_score is not None:
                if match.home_score > match.away_score:
                    stats.wins += 1
                elif match.home_score < match.away_score:
                    stats.losses += 1
                else:
                    stats.draws += 1
        
        # Aktualizácia štatistík pre hostujúci tím
        else:
            stats.goals_scored += match.away_score or 0
            stats.goals_conceded += match.home_score or 0
            
            if match.away_score is not None:
                if match.away_score > match.home_score:
                    stats.wins += 1
                elif match.away_score < match.home_score:
                    stats.losses += 1
                else:
                    stats.draws += 1
        
        stats.save()
        return stats

class PlayerManager:
    """
    Servisná trieda pre správu hráčov
    """
    @staticmethod
    def create_player(
        first_name, 
        last_name, 
        team, 
        position, 
        date_of_birth,
        nationality,
        jersey_number=None,
        height=None,
        weight=None,
        profile_image=None
    ):
        """
        Vytvorenie nového hráča
        """
        # Validácia povinných polí
        if not first_name or not last_name:
            raise ValidationError("Meno a priezvisko sú povinné")
        
        # Validácia veku
        age = (timezone.now().date() - date_of_birth).days / 365.25
        if age < 16:
            raise ValidationError("Hráč musí mať aspoň 16 rokov")
        
        player = Player.objects.create(
            first_name=first_name,
            last_name=last_name,
            team=team,
            position=position,
            date_of_birth=date_of_birth,
            nationality=nationality,
            jersey_number=jersey_number,
            height=height,
            weight=weight,
            profile_image=profile_image
        )
        
        return player

    @staticmethod
    def transfer_player(player, new_team):
        """
        Prestup hráča do iného tímu
        """
        # Zaznamenanie histórie prestupu
        PlayerTransfer.objects.create(
            player=player,
            from_team=player.team,
            to_team=new_team,
            transfer_date=timezone.now()
        )
        
        # Aktualizácia tímu hráča
        player.team = new_team
        player.save()
        
        return player

class Player(models.Model):
    """
    Model hráča
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    team = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='players')
    position = models.ForeignKey(PlayerPosition, on_delete=models.SET_NULL, null=True)
    
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=100)
    
    height = models.FloatField(null=True, blank=True)  # v cm
    weight = models.FloatField(null=True, blank=True)  # v kg
    
    jersey_number = models.IntegerField(null=True, blank=True)
    
    profile_image = models.ImageField(
        upload_to='player_images/', 
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """
        Výpočet veku hráča
        """
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

class TeamManagementService:
    """
    Servisná trieda pre správu tímov
    """
    @staticmethod
    def create_team(name, category, country, logo=None):
        """
        Vytvorenie nového tímu
        """
        team = Team.objects.create(
            name=name,
            category=category,
            country=country,
            logo=logo
        )
        
        # Automatické vytvorenie štatistík
        TeamStatistics.objects.create(team=team)
        
        return team

    @staticmethod
    def update_team_statistics(team, match):
        """
        Aktualizácia štatistík tímu po zápase
        """
        stats = team.statistics
        
        stats.total_matches += 1
        stats.goals_scored += match.home_score if match.home_team == team else match.away_score
        stats.goals_conceded += match.away_score if match.home_team == team else match.home_score
        
        if match.home_team == team:
            if match.home_score > match.away_score:
                stats.wins += 1
            elif match.home_score < match.away_score:
                stats.losses += 1
            else:
                stats.draws += 1
        else:
            if match.away_score > match.home_score:
                stats.wins += 1
            elif match.away_score < match.home_score:
                stats.losses += 1
            else:
                stats.draws += 1
        
        stats.save()

class TeamAnalytics:
    """
    Analytická trieda pre tímy
    """
    @staticmethod
    def get_team_performance(team, competition=None):
        """
        Komplexná analýza výkonnosti tímu
        """
        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        )
        
        if competition:
            matches = matches.filter(round__competition=competition)
        
        performance_data = {
            'total_matches': matches.count(),
            'wins': matches.filter(
                Q(home_team=team, home_score__gt=F('away_score')) | 
                Q(away_team=team, away_score__gt=F('home_score'))
            ).count(),
            'draws': matches.filter(
                Q(home_team=team, home_score=F('away_score')) | 
                Q(away_team=team, away_score=F('home_score'))
            ).count(),
            'losses': matches.filter(
                Q(home_team=team, home_score__lt=F('away_score')) | 
                Q(away_team=team, away_score__lt=F('home_score'))
            ).count(),
            'goals_scored': sum([
                match.home_score if match.home_team == team else match.away_score 
                for match in matches if match.home_score is not None
            ]),
            'goals_conceded': sum([
                match.away_score if match.home_team == team else match.home_score 
                for match in matches if match.away_score is not None
            ])
        }
        
        return performance_data

    @staticmethod
    def get_head_to_head(team1, team2, competition=None):
        """
        Analýza vzájomných zápasov
        """
        matches = Match.objects.filter(
            Q(home_team=team1, away_team=team2) | 
            Q(home_team=team2, away_team=team1)
        )
        
        if competition:
            matches = matches.filter(round__competition=competition)
        
        head_to_head_data = {
            'total_matches': matches.count(),
            'team1_wins': matches.filter(
                Q(home_team=team1, home_score__gt=F('away_score')) | 
                Q(away_team=team1, away_score__gt=F('home_score'))
            ).count(),
            'team2_wins': matches.filter(
                Q(home_team=team2, home_score__gt=F('away_score')) | 
                Q(away_team=team2, away_score__gt=F('home_score'))
            ).count(),
            'draws': matches.filter(home_score=F('away_score')).count(),
            'matches': [
                {
                    'match_date': match.match_date,
                    'home_team': match.home_team.name,
                    'away_team': match.away_team.name,
                    'home_score': match.home_score,
                    'away_score': match.away_score
                } for match in matches
            ]
        }
        
        return head_to_head_data