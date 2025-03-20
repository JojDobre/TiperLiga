from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import League, Competition, Round, Match, Team, Venue

class CompetitionStatus(models.TextChoices):
    """
    Stavy súťaže
    """
    NOT_STARTED = 'not_started', 'Nezačatá'
    IN_PROGRESS = 'in_progress', 'Prebieha'
    COMPLETED = 'completed', 'Ukončená'
    CANCELLED = 'cancelled', 'Zrušená'

class CompetitionCategory(models.Model):
    """
    Kategórie súťaží
    """
    name = models.CharField(max_length=100)
    sport = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class RoundManager:
    """
    Servisná trieda pre správu kôl
    """
    @staticmethod
    def create_round(
        competition, 
        name, 
        start_date, 
        end_date, 
        deadline
    ):
        """
        Vytvorenie nového kola v súťaži
        """
        # Validácia dátumov
        if start_date > end_date:
            raise ValidationError("Začiatočný dátum kola nemôže byť neskôr ako koncový dátum")
        
        if deadline > end_date:
            raise ValidationError("Termín uzávierky nemôže byť neskôr ako koncový dátum kola")
        
        round_obj = Round.objects.create(
            competition=competition,
            name=name,
            start_date=start_date,
            end_date=end_date,
            deadline=deadline
        )
        
        return round_obj

    @staticmethod
    def add_matches_to_round(
        round_obj, 
        matches_data
    ):
        """
        Pridanie zápasov do kola
        
        matches_data = [
            {
                'home_team': Team,
                'away_team': Team,
                'venue': Venue,
                'match_date': datetime
            },
            ...
        ]
        """
        created_matches = []
        
        for match_info in matches_data:
            match = Match.objects.create(
                round=round_obj,
                home_team=match_info['home_team'],
                away_team=match_info['away_team'],
                venue=match_info.get('venue'),
                match_date=match_info['match_date']
            )
            created_matches.append(match)
        
        return created_matches


class CompetitionManager:
    @staticmethod
    def create_competition(
        name, 
        category, 
        start_date, 
        end_date, 
        description=None, 
        leagues=None
    ):
        """
        Vytvorenie novej súťaže
        """
        # Validácia dátumov
        if start_date > end_date:
            raise ValidationError("Začiatočný dátum nemôže byť neskôr ako koncový dátum")
        
        competition = Competition.objects.create(
            name=name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            description=description,
            status=CompetitionStatus.NOT_STARTED
        )
        
        # Priradenie líg
        if leagues:
            competition.leagues.add(*leagues)
        
        return competition

    @staticmethod
    def update_competition_status(competition):
        """
        Automatická aktualizácia stavu súťaže
        """
        now = timezone.now().date()
        
        if now < competition.start_date:
            competition.status = CompetitionStatus.NOT_STARTED
        elif now > competition.end_date:
            competition.status = CompetitionStatus.COMPLETED
        else:
            competition.status = CompetitionStatus.IN_PROGRESS
        
        competition.save()
        return competition

    @staticmethod
    def create_rounds(competition, rounds_data):
        """
        Vytvorenie kôl pre súťaž
        
        rounds_data = [
            {
                'name': 'Základná skupina A',
                'deadline': datetime,
                'matches': [
                    {
                        'home_team': Team,
                        'away_team': Team,
                        'venue': Venue,
                        'match_date': datetime
                    },
                    ...
                ]
            },
            ...
        ]
        """
        created_rounds = []
        
        for round_data in rounds_data:
            round_obj = Round.objects.create(
                competition=competition,
                name=round_data['name'],
                deadline=round_data['deadline']
            )
            
            # Vytvorenie zápasov pre kolo
            matches = []
            for match_info in round_data.get('matches', []):
                match = Match.objects.create(
                    round=round_obj,
                    home_team=match_info['home_team'],
                    away_team=match_info['away_team'],
                    venue=match_info.get('venue'),
                    match_date=match_info['match_date']
                )
                matches.append(match)
            
            created_rounds.append({
                'round': round_obj,
                'matches': matches
            })
        
        return created_rounds

class LeagueOrganizer:
    @staticmethod
    def create_league(name, season, created_by, competitions=None):
        """
        Vytvorenie novej ligy
        """
        # Generovanie unikátneho ID pre ligu
        unique_id = f"{name.lower().replace(' ', '_')}_{season}"
        
        league = League.objects.create(
            name=name,
            season=season,
            unique_id=unique_id,
            created_by=created_by
        )
        
        if competitions:
            league.competitions.add(*competitions)
        
        return league

    @staticmethod
    def add_competitions_to_league(league, competitions):
        """
        Pridanie súťaží do ligy
        """
        league.competitions.add(*competitions)
        return league

    @staticmethod
    def get_league_competitions(league):
        """
        Získanie súťaží v lige
        """
        return league.competitions.all()

class CompetitionAnalytics:
    @staticmethod
    def get_competition_statistics(competition):
        """
        Základné štatistiky súťaže
        """
        rounds = Round.objects.filter(competition=competition)
        matches = Match.objects.filter(round__in=rounds)
        
        return {
            'total_rounds': rounds.count(),
            'total_matches': matches.count(),
            'completed_matches': matches.filter(home_score__isnull=False).count(),
            'start_date': competition.start_date,
            'end_date': competition.end_date,
            'current_status': CompetitionAnalytics._get_competition_status(competition)
        }

    @staticmethod
    def _get_competition_status(competition):
        """
        Určenie aktuálneho stavu súťaže
        """
        now = timezone.now()
        
        if now < competition.start_date:
            return 'not_started'
        elif now > competition.end_date:
            return 'completed'
        else:
            return 'in_progress'

    @staticmethod
    def get_team_performance(competition):
        """
        Výkonnosť tímov v súťaži
        """
        matches = Match.objects.filter(round__competition=competition)
        
        team_performance = {}
        
        for match in matches:
            # Spracovanie domácich tímov
            if match.home_team not in team_performance:
                team_performance[match.home_team] = {
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_scored': 0,
                    'goals_conceded': 0
                }
            
            # Spracovanie hostí
            if match.away_team not in team_performance:
                team_performance[match.away_team] = {
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_scored': 0,
                    'goals_conceded': 0
                }
            
            # Aktualizácia štatistík, ak je známy výsledok
            if match.home_score is not None and match.away_score is not None:
                home_team_stats = team_performance[match.home_team]
                away_team_stats = team_performance[match.away_team]
                
                home_team_stats['matches_played'] += 1
                away_team_stats['matches_played'] += 1
                
                home_team_stats['goals_scored'] += match.home_score
                home_team_stats['goals_conceded'] += match.away_score
                
                away_team_stats['goals_scored'] += match.away_score
                away_team_stats['goals_conceded'] += match.home_score
                
                if match.home_score > match.away_score:
                    home_team_stats['wins'] += 1
                    away_team_stats['losses'] += 1
                elif match.home_score < match.away_score:
                    home_team_stats['losses'] += 1
                    away_team_stats['wins'] += 1
                else:
                    home_team_stats['draws'] += 1
                    away_team_stats['draws'] += 1
        
        return team_performance