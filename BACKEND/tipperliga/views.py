from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import *
from .serializers import *
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import generate_league_leaderboards
from .authentication import generate_tokens
#from .notifications import NotificationViewSet
from .statistics import StatisticsService, ReportGenerator
from rest_framework.parsers import MultiPartParser, FormParser
from .social import SocialService, FriendRequest
from .profile import ProfileService
from .betting_system import BetService, BetChallengeSystem, BetChallenge, ValidationError
from .user_analytics import UserBettingProfile, UserLeaguePerformance
from .security import SecurityService, TwoFactorService, check_password, make_password
from .user_activity import UserSecurityAnalytics
from .notifications import NotificationService, UserNotificationPreference, NotificationType, Notification
from .reporting import Report, ReportType, ReportGenerationService
from .competition_management import CompetitionManager, RoundManager, CompetitionAnalytics
from .team_management import (
    TeamManager, 
    PlayerManager, 
    TeamCategory, 
    PlayerPosition
)
from .user_betting_history import (
    UserBettingHistoryService, 
    UserBettingTrendService
)




class SocialViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['GET'])
    def friend_requests(self, request):
        """
        Zoznam prijatých a odoslaných žiadostí o priateľstvo
        """
        received_requests = FriendRequest.objects.filter(
            receiver=request.user, 
            status='pending'
        )
        sent_requests = FriendRequest.objects.filter(
            sender=request.user, 
            status='pending'
        )

        return Response({
            'received_requests': FriendRequestSerializer(received_requests, many=True).data,
            'sent_requests': FriendRequestSerializer(sent_requests, many=True).data
        })

    @action(detail=False, methods=['POST'])
    def send_friend_request(self, request):
        """
        Odoslanie žiadosti o priateľstvo
        """
        receiver_id = request.data.get('receiver_id')
        
        try:
            receiver = CustomUser.objects.get(id=receiver_id)
            friend_request = SocialService.send_friend_request(request.user, receiver)
            
            return Response({
                'message': 'Žiadosť o priateľstvo bola odoslaná',
                'request_id': friend_request.id
            }, status=status.HTTP_201_CREATED)
        
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Užívateľ nebol nájdený'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def accept_friend_request(self, request):
        """
        Prijatie žiadosti o priateľstvo
        """
        request_id = request.data.get('request_id')
        
        try:
            friend_request = SocialService.accept_friend_request(request_id, request.user)
            
            return Response({
                'message': 'Žiadosť o priateľstvo bola prijatá',
                'friend_id': friend_request.sender.id
            })
        
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def reject_friend_request(self, request):
        """
        Zamietnutie žiadosti o priateľstvo
        """
        request_id = request.data.get('request_id')
        
        try:
            SocialService.reject_friend_request(request_id, request.user)
            
            return Response({
                'message': 'Žiadosť o priateľstvo bola zamietnutá'
            })
        
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def my_friends(self, request):
        """
        Zoznam priateľov
        """
        friends = SocialService.get_friends(request.user)
        
        return Response({
            'friends': UserSerializer(friends, many=True).data
        })

    @action(detail=False, methods=['POST'])
    def remove_friend(self, request):
        """
        Odstránenie priateľa
        """
        friend_id = request.data.get('friend_id')
        
        try:
            friend = CustomUser.objects.get(id=friend_id)
            result = SocialService.remove_friend(request.user, friend)
            
            if result:
                return Response({
                    'message': 'Priateľ bol odstránený'
                })
            else:
                return Response({
                    'error': 'Priateľstvo nebolo nájdené'
                }, status=status.HTTP_404_NOT_FOUND)
        
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Užívateľ nebol nájdený'
            }, status=status.HTTP_404_NOT_FOUND)


class UserProfileViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser]
    
    @action(detail=False, methods=['GET'])
    def my_profile(self, request):
        """
        Načítanie vlastného profilu
        """
        profile_details = ProfileService.get_user_profile_details(request.user)
        return Response(profile_details)
    
    @action(detail=False, methods=['PUT'], parser_classes=[MultiPartParser, FormParser])
    def update_profile(self, request):
        """
        Aktualizácia profilu a nastavení
        """
        # Spracovanie profilových dát
        profile_data = {
            'display_name': request.data.get('display_name'),
            'bio': request.data.get('bio'),
            'avatar': request.FILES.get('avatar')
        }
        
        # Spracovanie nastavení
        settings_data = {
            'interface_theme': request.data.get('theme'),
            'language': request.data.get('language'),
            'notification_frequency': request.data.get('notification_frequency')
        }
        
        # Odstránenie None hodnôt
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        settings_data = {k: v for k, v in settings_data.items() if v is not None}
        
        try:
            updated_profile = ProfileService.update_profile(
                request.user, 
                profile_data, 
                settings_data
            )
            
            return Response({
                'message': 'Profil úspešne aktualizovaný',
                'profile': UserProfileSerializer(updated_profile).data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Prihlásenie užívateľa
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        tokens = generate_tokens(user)
        return Response(tokens, status=status.HTTP_200_OK)
    
    return Response({
        'error': 'Neplatné prihlasovacie údaje'
    }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Obnovenie access tokenu
    """
    refresh_token = request.data.get('refresh')
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        return Response({
            'access': access_token
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Neplatný refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)

class UserViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        """
        Štatistiky pre konkrétneho užívateľa
        """
        user = self.get_object()
        stats = StatisticsService.get_user_overall_statistics(user)
        return Response(stats)
    
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user).data,
            "message": "Užívateľ úspešne zaregistrovaný"
        }, status=status.HTTP_201_CREATED)

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        """
        Štatistiky tímu
        """
        team = self.get_object()
        stats = team.statistics
        
        return Response({
            'total_matches': stats.total_matches,
            'wins': stats.wins,
            'draws': stats.draws,
            'losses': stats.losses,
            'goals_scored': stats.goals_scored,
            'goals_conceded': stats.goals_conceded,
            'win_percentage': stats.win_percentage,
            'goal_difference': stats.goal_difference
        })

    @action(detail=True, methods=['GET'])
    def players(self, request, pk=None):
        """
        Zoznam hráčov tímu
        """
        team = self.get_object()
        players = team.player_set.all()
        
        return Response({
            'players': PlayerSerializer(players, many=True).data
        })

    @action(detail=False, methods=['GET'])
    def categories(self, request):
        """
        Zoznam kategórií tímov
        """
        categories = TeamCategory.objects.all()
        return Response({
            'categories': TeamCategorySerializer(categories, many=True).data
        })

class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer

    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        """
        Komplexné štatistiky pre ligu
        """
        league = self.get_object()
        stats = StatisticsService.generate_league_report(league)
        return Response(stats)

    @action(detail=True, methods=['GET'])
    def generate_report(self, request, pk=None):
        """
        Vygenerovanie reportu pre ligu
        """
        league = self.get_object()
        report_type = request.query_params.get('type', 'monthly')
        
        report = ReportGenerator.generate_periodic_report(league, report_type)
        
        return Response({
            'report_id': report.id,
            'created_at': report.created_at,
            'type': report.report_type
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['GET'])
    def leaderboard(self, request, pk=None):
        """
        Endpoint pre zobrazenie rebríčka ligy
        """
        league = self.get_object()
        leaderboard = LeagueScoring.get_league_leaderboard(league)
        return Response(leaderboard)

    @action(detail=False, methods=['GET'])
    def all_leaderboards(self, request):
        """
        Endpoint pre všetky rebríčky
        """
        leaderboards = generate_league_leaderboards.delay()
        return Response({"task_id": leaderboards.id})

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer

    @action(detail=True, methods=['post'])
    def place_bet(self, request, pk=None):
        match = self.get_object()
        serializer = BetSerializer(data=request.data, context={'match': match})
        
        if serializer.is_valid():
            bet = serializer.save(user=request.user, match=match)
            return Response(BetSerializer(bet).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AchievementType.objects.all()
    serializer_class = AchievementTypeSerializer

    @action(detail=False, methods=['GET'])
    def user_achievements(self, request):
        """
        Zoznam achievementov pre aktuálneho užívateľa
        """
        user_achievements = UserAchievement.objects.filter(user=request.user)
        serializer = UserAchievementSerializer(user_achievements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def claim_achievement(self, request, pk=None):
        """
        Prevzatie achievementu
        """
        achievement = self.get_object()
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=request.user,
            achievement_type=achievement
        )
        
        if not user_achievement.is_claimed:
            user_achievement.is_claimed = True
            user_achievement.save()
            
            # Pridanie bodov
            request.user.points += achievement.points_reward
            request.user.save()
            
            return Response({
                'status': 'Achievement claimed',
                'points_earned': achievement.points_reward
            })
        
        return Response({
            'status': 'Achievement already claimed'
        }, status=status.HTTP_400_BAD_REQUEST)
    
class CompetitionViewSet(viewsets.ModelViewSet):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer
    
    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        """
        Štatistiky súťaže
        """
        competition = self.get_object()
        stats = CompetitionAnalytics.get_competition_statistics(competition)
        return Response(stats)
    
    @action(detail=True, methods=['GET'])
    def team_performance(self, request, pk=None):
        """
        Výkonnosť tímov v súťaži
        """
        competition = self.get_object()
        performance = CompetitionAnalytics.get_team_performance(competition)
        return Response(performance)
    
    @action(detail=True, methods=['POST'])
    def create_round(self, request, pk=None):
        """
        Vytvorenie nového kola v súťaži
        """
        competition = self.get_object()
        
        try:
            round_obj = RoundManager.create_round(
                competition=competition,
                name=request.data.get('name'),
                start_date=request.data.get('start_date'),
                end_date=request.data.get('end_date'),
                deadline=request.data.get('deadline')
            )
            
            return Response({
                'message': 'Kolo bolo vytvorené',
                'round_id': round_obj.id
            }, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class LeagueViewSet(viewsets.ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    
    @action(detail=True, methods=['POST'])
    def add_competitions(self, request, pk=None):
        """
        Pridanie súťaží do ligy
        """
        league = self.get_object()
        competition_ids = request.data.get('competitions', [])
        
        try:
            competitions = Competition.objects.filter(id__in=competition_ids)
            updated_league = LeagueOrganizer.add_competitions_to_league(league, competitions)
            
            return Response({
                'message': 'Súťaže boli pridané do ligy',
                'competitions': CompetitionSerializer(updated_league.competitions.all(), many=True).data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['GET'])
    def competitions(self, request, pk=None):
        """
        Zoznam súťaží v lige
        """
        league = self.get_object()
        competitions = LeagueOrganizer.get_league_competitions(league)
        
        return Response({
            'competitions': CompetitionSerializer(competitions, many=True).data
        })

class BetViewSet(viewsets.ModelViewSet):
    queryset = Bet.objects.all()
    serializer_class = BetSerializer

    @action(detail=False, methods=['POST'])
    def place_bet(self, request):
        """
        Umiestnenie tipu
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_id = request.data.get('match_id')
        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')

        try:
            match = Match.objects.get(id=match_id)
            bet = BetService.place_bet(request.user, match, home_score, away_score)
            
            return Response({
                'message': 'Tip bol úspešne umiestnený',
                'bet': BetSerializer(bet).data
            }, status=status.HTTP_201_CREATED)
        
        except (Match.DoesNotExist, ValidationError) as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['PUT'])
    def update_bet(self, request, pk=None):
        """
        Aktualizácia tipu
        """
        bet = self.get_object()
        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')

        try:
            updated_bet = BetService.update_bet(bet, home_score, away_score)
            
            return Response({
                'message': 'Tip bol úspešne aktualizovaný',
                'bet': BetSerializer(updated_bet).data
            })
        
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def my_bets(self, request):
        """
        Zoznam tipov prihláseneho užívateľa
        """
        league_id = request.query_params.get('league_id')
        competition_id = request.query_params.get('competition_id')

        league = League.objects.get(id=league_id) if league_id else None
        competition = Competition.objects.get(id=competition_id) if competition_id else None

        bets = BetService.get_user_bets(request.user, league, competition)
        
        return Response({
            'bets': BetSerializer(bets, many=True).data
        })

class BetChallengeViewSet(viewsets.ModelViewSet):
    queryset = BetChallenge.objects.all()
    serializer_class = BetChallengeSerializer

    @action(detail=False, methods=['POST'])
    def create_challenge(self, request):
        """
        Vytvorenie výzvy na stávku
        """
        match_id = request.data.get('match_id')
        challenged_user_id = request.data.get('challenged_user_id')
        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')
        stake = request.data.get('stake')

        try:
            match = Match.objects.get(id=match_id)
            challenged_user = CustomUser.objects.get(id=challenged_user_id)
            
            challenge = BetChallengeSystem.create_bet_challenge(
                request.user, 
                challenged_user, 
                match, 
                stake
            )
            
            return Response({
                'message': 'Výzva na stávku bola vytvorená',
                'challenge': BetChallengeSerializer(challenge).data
            }, status=status.HTTP_201_CREATED)
        
        except (Match.DoesNotExist, CustomUser.DoesNotExist, ValidationError) as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def accept_challenge(self, request, pk=None):
        """
        Prijatie výzvy na stávku
        """
        challenge = self.get_object()
        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')

        try:
            updated_challenge = BetChallengeSystem.accept_bet_challenge(
                challenge, 
                home_score, 
                away_score
            )
            
            return Response({
                'message': 'Výzva na stávku bola prijatá',
                'challenge': BetChallengeSerializer(updated_challenge).data
            })
        
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    @action(detail=True, methods=['GET'])
    def statistics(self, request, pk=None):
        """
        Štatistiky tímu
        """
        team = self.get_object()
        stats = TeamAnalytics.get_team_performance(team)
        
        return Response(stats)

    @action(detail=True, methods=['GET'])
    def players(self, request, pk=None):
        """
        Zoznam hráčov tímu
        """
        team = self.get_object()
        players = team.players.all()
        
        return Response({
            'players': PlayerSerializer(players, many=True).data
        })

    @action(detail=True, methods=['GET'])
    def head_to_head(self, request, pk=None):
        """
        Analýza vzájomných zápasov
        """
        team = self.get_object()
        opponent_id = request.query_params.get('opponent_id')
        competition_id = request.query_params.get('competition_id')

        try:
            opponent = Team.objects.get(id=opponent_id)
            competition = Competition.objects.get(id=competition_id) if competition_id else None
            
            head_to_head_data = TeamAnalytics.get_head_to_head(team, opponent, competition)
            
            return Response(head_to_head_data)
        
        except (Team.DoesNotExist, Competition.DoesNotExist) as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    @action(detail=True, methods=['POST'])
    def transfer(self, request, pk=None):
        """
        Prestup hráča
        """
        player = self.get_object()
        new_team_id = request.data.get('new_team_id')
        
        try:
            new_team = Team.objects.get(id=new_team_id)
            transferred_player = PlayerManager.transfer_player(player, new_team)
            
            return Response({
                'message': 'Hráč bol presunutý do nového tímu',
                'player': PlayerSerializer(transferred_player).data
            })
        
        except Team.DoesNotExist:
            return Response({
                'error': 'Cieľový tím nebol nájdený'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['GET'])
    def transfer_history(self, request, pk=None):
        """
        História prestupov hráča
        """
        player = self.get_object()
        transfers = PlayerTransfer.objects.filter(player=player)
        
        return Response({
            'transfers': PlayerTransferSerializer(transfers, many=True).data
        })

    @action(detail=False, methods=['GET'])
    def positions(self, request):
        """
        Zoznam pozícií hráčov
        """
        positions = PlayerPosition.objects.all()
        return Response({
            'positions': PlayerPositionSerializer(positions, many=True).data
        })

    @action(detail=True, methods=['GET'])
    def performance(self, request, pk=None):
        """
        Výkonnosť hráča
        """
        player = self.get_object()
        # Tu môžete pridať logiku pre sledovanie výkonnosti hráča
        return Response({
            'player_id': player.id,
            'name': f"{player.first_name} {player.last_name}",
            'position': player.position.name if player.position else None
        })

class UserAnalyticsViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['GET'])
    def overall_statistics(self, request):
        """
        Celkové štatistiky tipov užívateľa
        """
        stats = UserBettingProfile.get_overall_betting_statistics(request.user)
        return Response(stats)

    @action(detail=False, methods=['GET'])
    def betting_trends(self, request):
        """
        Trendy tipov za dané obdobie
        """
        period_days = request.query_params.get('period', 30)
        trends = UserBettingProfile.get_betting_trends(request.user, int(period_days))
        
        return Response({
            'trends': trends,
            'period_days': period_days
        })

    @action(detail=False, methods=['GET'])
    def competition_performance(self, request):
        """
        Výkonnosť podľa súťaží
        """
        performance = UserBettingProfile.get_performance_by_competition(request.user)
        
        return Response({
            'competition_performance': performance
        })

    @action(detail=False, methods=['GET'])
    def most_successful_teams(self, request):
        """
        Najúspešnejšie tímy
        """
        teams = UserBettingProfile.get_most_successful_teams(request.user)
        
        return Response({
            'teams': teams
        })

    @action(detail=False, methods=['GET'])
    def league_performance(self, request):
        """
        Výkonnosť užívateľa v ligách
        """
        league_id = request.query_params.get('league_id')
        
        try:
            league = League.objects.get(id=league_id)
            performance = UserLeaguePerformance.objects.get(
                user=request.user, 
                league=league
            )
            
            return Response({
                'league_name': league.name,
                'total_bets': performance.total_bets,
                'total_points': performance.total_points,
                'rank': performance.rank
            })
        
        except (League.DoesNotExist, UserLeaguePerformance.DoesNotExist):
            return Response({
                'error': 'Žiadne údaje pre danú ligu'
            }, status=status.HTTP_404_NOT_FOUND)
        
class SecurityViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['POST'])
    def change_password(self, request):
        """
        Zmena hesla prihláseného užívateľa
        """
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        # Overenie súčasného hesla
        if not check_password(old_password, request.user.password):
            return Response({
                'error': 'Nesprávne súčasné heslo'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validácia nového hesla
        is_valid, message = SecurityService.validate_password(new_password)
        if not is_valid:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Zmena hesla
        request.user.password = make_password(new_password)
        request.user.save()
        
        return Response({
            'message': 'Heslo bolo úspešne zmenené'
        })

    @action(detail=False, methods=['POST'])
    def initiate_password_reset(self, request):
        """
        Inicializácia procesu obnovenia hesla
        """
        email = request.data.get('email')
        
        try:
            user = CustomUser.objects.get(email=email)
            reset_token = SecurityService.initiate_password_reset(user)
            
            return Response({
                'message': 'Inštrukcie na obnovenie hesla boli odoslané na váš email'
            })
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Užívateľ s týmto emailom neexistuje'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST'])
    def reset_password(self, request):
        """
        Obnovenie hesla pomocou tokenu
        """
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        try:
            SecurityService.reset_password(token, new_password)
            
            return Response({
                'message': 'Heslo bolo úspešne obnovené'
            })
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class TwoFactorViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['POST'])
    def enable(self, request):
        """
        Aktivácia dvojfaktorovej autentifikácie
        """
        try:
            two_factor_data = TwoFactorService.enable_two_factor(request.user)
            
            return Response({
                'message': 'Dvojfaktorová autentifikácia bola aktivovaná',
                'backup_codes': two_factor_data['backup_codes']
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def disable(self, request):
        """
        Deaktivácia dvojfaktorovej autentifikácie
        """
        result = TwoFactorService.disable_two_factor(request.user)
        
        if result:
            return Response({
                'message': 'Dvojfaktorová autentifikácia bola deaktivovaná'
            })
        else:
            return Response({
                'error': 'Dvojfaktorová autentifikácia nie je aktivovaná'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'])
    def verify(self, request):
        """
        Overenie dvojfaktorového kódu
        """
        code = request.data.get('code')
        
        if TwoFactorService.verify_two_factor(request.user, code):
            return Response({
                'message': 'Kód bol úspešne overený'
            })
        else:
            return Response({
                'error': 'Neplatný overovací kód'
            }, status=status.HTTP_400_BAD_REQUEST)
        
class UserActivityViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['GET'])
    def recent_activities(self, request):
        """
        Zobrazenie nedávnych aktivít
        """
        days = request.query_params.get('days', 30)
        activities = UserSecurityAnalytics.get_recent_activities(
            request.user, 
            int(days)
        )
        
        return Response({
            'activities': UserActivityLogSerializer(activities, many=True).data,
            'period_days': days
        })

    @action(detail=False, methods=['GET'])
    def devices(self, request):
        """
        Zoznam prihlásených zariadení
        """
        devices = UserDeviceInfo.objects.filter(user=request.user)
        
        return Response({
            'devices': UserDeviceInfoSerializer(devices, many=True).data
        })

    @action(detail=False, methods=['GET'])
    def suspicious_activities(self, request):
        """
        Detekcia podozrivých aktivít
        """
        suspicious_activities = UserSecurityAnalytics.detect_suspicious_activities(request.user)
        
        return Response({
            'suspicious_activities': suspicious_activities
        })
    
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Vrátenie notifikácií pre aktuálneho užívateľa
        """
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['GET'])
    def unread_count(self, request):
        """
        Počet neprečítaných notifikácií
        """
        unread_count = Notification.objects.filter(
            user=request.user, 
            status='unread'
        ).count()
        
        return Response({
            'unread_count': unread_count
        })

    @action(detail=False, methods=['POST'])
    def mark_all_read(self, request):
        """
        Označenie všetkých notifikácií ako prečítaných
        """
        Notification.objects.filter(
            user=request.user, 
            status='unread'
        ).update(status='read')
        
        return Response({
            'message': 'Všetky notifikácie boli označené ako prečítané'
        })

    @action(detail=True, methods=['POST'])
    def mark_read(self, request, pk=None):
        """
        Označenie konkrétnej notifikácie ako prečítanej
        """
        notification = self.get_object()
        notification.status = 'read'
        notification.save()
        
        return Response({
            'message': 'Notifikácia bola označená ako prečítaná'
        })

class NotificationPreferencesViewSet(viewsets.ModelViewSet):
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Vrátenie nastavení notifikácií pre aktuálneho užívateľa
        """
        return UserNotificationPreference.objects.filter(user=self.request.user)

    @action(detail=False, methods=['GET'])
    def available_types(self, request):
        """
        Zoznam dostupných typov notifikácií
        """
        types = NotificationType.objects.all()
        return Response({
            'notification_types': NotificationTypeSerializer(types, many=True).data
        })

class RoundViewSet(viewsets.ModelViewSet):
    queryset = Round.objects.all()
    serializer_class = RoundSerializer

    @action(detail=True, methods=['POST'])
    def add_matches(self, request, pk=None):
        """
        Pridanie zápasov do kola
        """
        round_obj = self.get_object()
        matches_data = request.data.get('matches', [])
        
        try:
            # Spracovanie tímov a venue
            processed_matches = []
            for match_info in matches_data:
                home_team = Team.objects.get(id=match_info['home_team_id'])
                away_team = Team.objects.get(id=match_info['away_team_id'])
                venue = Venue.objects.get(id=match_info.get('venue_id')) if match_info.get('venue_id') else None
                
                processed_matches.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'venue': venue,
                    'match_date': match_info['match_date']
                })
            
            # Pridanie zápasov
            created_matches = RoundManager.add_matches_to_round(
                round_obj, 
                processed_matches
            )
            
            return Response({
                'message': 'Zápasy boli pridané do kola',
                'matches': [match.id for match in created_matches]
            }, status=status.HTTP_201_CREATED)
        
        except (Team.DoesNotExist, Venue.DoesNotExist) as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)   

class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Vrátenie reportov pre aktuálneho užívateľa
        """
        return Report.objects.filter(user=self.request.user)

    @action(detail=False, methods=['POST'])
    def generate_user_report(self, request):
        """
        Vygenerovanie reportu pre užívateľa
        """
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        # Získanie typu reportu pre užívateľa
        report_type, _ = ReportType.objects.get_or_create(
            name='Užívateľský betting report',
            category='user'
        )
        
        report = ReportGenerationService.create_report(
            request.user, 
            report_type, 
            start_date, 
            end_date
        )
        
        return Response({
            'message': 'Report bol naplánovaný na generovanie',
            'report_id': report.id
        })

    @action(detail=False, methods=['POST'])
    def generate_league_report(self, request):
        """
        Vygenerovanie reportu pre ligu
        """
        league_id = request.data.get('league_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        try:
            league = League.objects.get(id=league_id)
            
            # Získanie typu reportu pre ligu
            report_type, _ = ReportType.objects.get_or_create(
                name=f'Report ligy {league.name}',
                category='league'
            )
            
            report = ReportGenerationService.create_report(
                request.user, 
                report_type, 
                start_date, 
                end_date,
                {'league_id': league_id}
            )
            
            return Response({
                'message': 'Report ligy bol naplánovaný na generovanie',
                'report_id': report.id
            })
        
        except League.DoesNotExist:
            return Response({
                'error': 'Liga nebola nájdená'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST'])
    def generate_competition_report(self, request):
        """
        Vygenerovanie reportu pre súťaž
        """
        competition_id = request.data.get('competition_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        try:
            competition = Competition.objects.get(id=competition_id)
            
            # Získanie typu reportu pre súťaž
            report_type, _ = ReportType.objects.get_or_create(
                name=f'Report súťaže {competition.name}',
                category='competition'
            )
            
            report = ReportGenerationService.create_report(
                request.user, 
                report_type, 
                start_date, 
                end_date,
                {'competition_id': competition_id}
            )
            
            return Response({
                'message': 'Report súťaže bol naplánovaný na generovanie',
                'report_id': report.id
            })
        
        except Competition.DoesNotExist:
            return Response({
                'error': 'Súťaž nebola nájdená'
            }, status=status.HTTP_404_NOT_FOUND)

class UserBettingHistoryViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['GET'])
    def history(self, request):
        """
        História tipov s možnosťou filtrácie
        """
        filters = {
            'competition_id': request.query_params.get('competition_id'),
            'league_id': request.query_params.get('league_id'),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
            'is_correct': request.query_params.get('is_correct')
        }
        
        # Odstránenie None hodnôt z filtrov
        filters = {k: v for k, v in filters.items() if v is not None}
        
        history_entries = UserBettingHistoryService.get_user_betting_history(
            request.user, 
            filters
        )
        
        return Response({
            'history': UserBettingHistoryEntrySerializer(history_entries, many=True).data,
            'filters': filters
        })

    @action(detail=False, methods=['GET'])
    def summary(self, request):
        """
        Súhrn tipovacích aktivít
        """
        period_days = int(request.query_params.get('period', 30))
        
        summary = UserBettingHistoryService.get_user_betting_summary(
            request.user, 
            period_days
        )
        
        return Response({
            'summary': summary,
            'period_days': period_days
        })

    @action(detail=False, methods=['GET'])
    def trends(self, request):
        """
        Trendy tipov
        """
        period_days = int(request.query_params.get('period', 30))
        
        trends = UserBettingTrendService.get_user_betting_trends(
            request.user, 
            period_days
        )
        
        return Response({
            'trends': UserBettingTrendSerializer(trends, many=True).data,
            'period_days': period_days
        })