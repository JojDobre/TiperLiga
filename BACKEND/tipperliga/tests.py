from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import League, Competition, Round, Match, Team, Bet
from .profile import UserProfile

User = get_user_model()

class LeagueCreationTestCase(TestCase):
    def setUp(self):
        # Príprava testovacie prostredia
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_league(self):
        """
        Test vytvorenia ligy
        """
        league_data = {
            'name': 'Test Liga',
            'season': '2024/25',
            'unique_id': 'test_liga_2024'
        }
        
        response = self.client.post('/api/leagues/', league_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(League.objects.count(), 1)
        self.assertEqual(League.objects.first().name, 'Test Liga')

class CompetitionManagementTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Vytvorenie testovacej ligy
        self.league = League.objects.create(
            name='Test Liga',
            season='2024/25',
            unique_id='test_liga_2024',
            created_by=self.user
        )

    def test_create_competition(self):
        """
        Test vytvorenia súťaže
        """
        competition_data = {
            'name': 'Testovacia Súťaž',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'leagues': [self.league.id]
        }
        
        response = self.client.post('/api/competitions/', competition_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Competition.objects.first().name, 'Testovacia Súťaž')

class BettingSystemTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='betuser', 
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Príprava testovacej súťaže a zápasu
        self.league = League.objects.create(
            name='Test Liga',
            season='2024/25',
            unique_id='test_liga_2024',
            created_by=self.user
        )
        
        self.competition = Competition.objects.create(
            name='Testovacia Súťaž',
            start_date='2024-01-01',
            end_date='2024-12-31'
        )
        self.competition.leagues.add(self.league)
        
        self.round = Round.objects.create(
            competition=self.competition,
            name='Prvé kolo',
            deadline='2024-02-01T20:00:00Z'
        )
        
        self.home_team = Team.objects.create(name='Domáci')
        self.away_team = Team.objects.create(name='Hostia')
        
        self.match = Match.objects.create(
            round=self.round,
            home_team=self.home_team,
            away_team=self.away_team,
            match_date='2024-02-02T18:00:00Z'
        )

    def test_place_bet(self):
        """
        Test umiestnenia tipu
        """
        bet_data = {
            'match_id': self.match.id,
            'home_score': 2,
            'away_score': 1
        }
        
        response = self.client.post('/api/bets/place/', bet_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bet.objects.count(), 1)
        
        bet = Bet.objects.first()
        self.assertEqual(bet.home_score_prediction, 2)
        self.assertEqual(bet.away_score_prediction, 1)

class ScoringSystemTestCase(TestCase):
    def setUp(self):
        # Príprava testovacie prostredia pre bodovací systém
        pass

    def test_scoring_calculation(self):
        """
        Test výpočtu bodov za tip
        """
        # Implementácia testu bodovacieho systému
        pass