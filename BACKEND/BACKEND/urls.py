
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tipperliga.views import (
    UserViewSet, TeamViewSet, LeagueViewSet, MatchViewSet,
    login_view, refresh_token_view, UserProfileViewSet, SocialViewSet, CompetitionViewSet, BetViewSet, 
    BetChallengeViewSet, PlayerViewSet, UserAnalyticsViewSet, SecurityViewSet, TwoFactorViewSet, 
    UserAchievement, UserActivityViewSet, NotificationViewSet, NotificationPreferencesViewSet, ReportViewSet, 
    RoundViewSet, TeamViewSet, PlayerViewSet, UserBettingHistoryViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'leagues', LeagueViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'competitions', CompetitionViewSet)
router.register(r'bets', BetViewSet, basename='bet')
router.register(r'bet-challenges', BetChallengeViewSet, basename='bet-challenge')
router.register(r'social', SocialViewSet, basename='social')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'players', PlayerViewSet)
router.register(r'user-analytics', UserAnalyticsViewSet, basename='user-analytics')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api/', include('tipperliga.urls')),  # Uistite sa, že máte tento riadok
    path('auth/login/', login_view, name='login'),
    path('auth/refresh/', refresh_token_view, name='refresh_token'),
    path('profile/', UserProfileViewSet.as_view({
        'get': 'my_profile',
        'put': 'update_profile'
    })),
    path('social/', SocialViewSet.as_view({
        'get': 'friend_requests'
    })),
    path('social/send-request/', SocialViewSet.as_view({
        'post': 'send_friend_request'
    })),
    path('social/accept-request/', SocialViewSet.as_view({
        'post': 'accept_friend_request'
    })),
    path('social/reject-request/', SocialViewSet.as_view({
        'post': 'reject_friend_request'
    })),
    path('social/friends/', SocialViewSet.as_view({
        'get': 'my_friends'
    })),
    path('social/remove-friend/', SocialViewSet.as_view({
        'post': 'remove_friend'
    })),
    path('competitions/', CompetitionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('competitions/<int:pk>/', CompetitionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('competitions/<int:pk>/statistics/', CompetitionViewSet.as_view({
        'get': 'statistics'
    })),
    path('competitions/<int:pk>/team-performance/', CompetitionViewSet.as_view({
        'get': 'team_performance'
    })),
    path('leagues/', LeagueViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('leagues/<int:pk>/', LeagueViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('leagues/<int:pk>/add-competitions/', LeagueViewSet.as_view({
        'post': 'add_competitions'
    })),
    path('leagues/<int:pk>/competitions/', LeagueViewSet.as_view({
        'get': 'competitions'
    })),
        path('bets/place/', BetViewSet.as_view({
        'post': 'place_bet'
    })),
    path('bets/my-bets/', BetViewSet.as_view({
        'get': 'my_bets'
    })),
    path('bets/<int:pk>/update/', BetViewSet.as_view({
        'put': 'update_bet'
    })),
    path('bet-challenges/create/', BetChallengeViewSet.as_view({
        'post': 'create_challenge'
    })),
    path('bet-challenges/<int:pk>/accept/', BetChallengeViewSet.as_view({
        'post': 'accept_challenge'
    })),
    path('teams/', TeamViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('teams/<int:pk>/', TeamViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('teams/<int:pk>/statistics/', TeamViewSet.as_view({
        'get': 'statistics'
    })),
    path('teams/<int:pk>/players/', TeamViewSet.as_view({
        'get': 'players'
    })),
    path('teams/<int:pk>/head-to-head/', TeamViewSet.as_view({
        'get': 'head_to_head'
    })),
    path('players/', PlayerViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('players/<int:pk>/', PlayerViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('players/<int:pk>/performance/', PlayerViewSet.as_view({
        'get': 'performance'
    })),
    path('user-analytics/overall-statistics/', UserAnalyticsViewSet.as_view({
        'get': 'overall_statistics'
    })),
    path('user-analytics/betting-trends/', UserAnalyticsViewSet.as_view({
        'get': 'betting_trends'
    })),
    path('user-analytics/competition-performance/', UserAnalyticsViewSet.as_view({
        'get': 'competition_performance'
    })),
    path('user-analytics/most-successful-teams/', UserAnalyticsViewSet.as_view({
        'get': 'most_successful_teams'
    })),
    path('user-analytics/league-performance/', UserAnalyticsViewSet.as_view({
        'get': 'league_performance'
    })),
    path('security/change-password/', SecurityViewSet.as_view({
        'post': 'change_password'
    })),
    path('security/initiate-password-reset/', SecurityViewSet.as_view({
        'post': 'initiate_password_reset'
    })),
    path('security/reset-password/', SecurityViewSet.as_view({
        'post': 'reset_password'
    })),
    path('security/two-factor/enable/', TwoFactorViewSet.as_view({
        'post': 'enable'
    })),
    path('security/two-factor/disable/', TwoFactorViewSet.as_view({
        'post': 'disable'
    })),
    path('security/two-factor/verify/', TwoFactorViewSet.as_view({
        'post': 'verify'
    })),
    path('activity/recent/', UserActivityViewSet.as_view({
        'get': 'recent_activities'
    })),
    path('activity/devices/', UserActivityViewSet.as_view({
        'get': 'devices'
    })),
    path('activity/suspicious/', UserActivityViewSet.as_view({
        'get': 'suspicious_activities'
    })),
    path('notifications/', NotificationViewSet.as_view({
        'get': 'list'
    })),
    path('notifications/unread-count/', NotificationViewSet.as_view({
        'get': 'unread_count'
    })),
    path('notifications/mark-all-read/', NotificationViewSet.as_view({
        'post': 'mark_all_read'
    })),
    path('notifications/<int:pk>/mark-read/', NotificationViewSet.as_view({
        'post': 'mark_read'
    })),
    path('notification-preferences/', NotificationPreferencesViewSet.as_view({
        'get': 'list'
    })),
    path('notification-preferences/types/', NotificationPreferencesViewSet.as_view({
        'get': 'available_types'
    })),
    path('reports/', ReportViewSet.as_view({
        'get': 'list'
    })),
    path('reports/generate-user/', ReportViewSet.as_view({
        'post': 'generate_user_report'
    })),
    path('reports/generate-league/', ReportViewSet.as_view({
        'post': 'generate_league_report'
    })),
    path('reports/generate-competition/', ReportViewSet.as_view({
        'post': 'generate_competition_report'
    })),
    path('user-analytics/statistics/', UserAnalyticsViewSet.as_view({
        'get': 'betting_statistics'
    })),
    path('user-analytics/daily-trends/', UserAnalyticsViewSet.as_view({
        'get': 'daily_trends'
    })),
    path('user-analytics/league-performance/', UserAnalyticsViewSet.as_view({
        'get': 'league_performance'
    })),
    path('competitions/<int:pk>/create-round/', CompetitionViewSet.as_view({
        'post': 'create_round'
    })),
    path('rounds/', RoundViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('rounds/<int:pk>/', RoundViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
    path('rounds/<int:pk>/add-matches/', RoundViewSet.as_view({
        'post': 'add_matches'
    })),




    # Tímy
    path('teams/categories/', TeamViewSet.as_view({
        'get': 'categories'
    })),
    
    # Hráči
    path('players/<int:pk>/transfer/', PlayerViewSet.as_view({
        'post': 'transfer'
    })),
    path('players/<int:pk>/transfer-history/', PlayerViewSet.as_view({
        'get': 'transfer_history'
    })),
    path('players/positions/', PlayerViewSet.as_view({
        'get': 'positions'
    })),
    path('betting-history/', UserBettingHistoryViewSet.as_view({
        'get': 'history'
    })),
    path('betting-history/summary/', UserBettingHistoryViewSet.as_view({
        'get': 'summary'
    })),
    path('betting-history/trends/', UserBettingHistoryViewSet.as_view({
        'get': 'trends'
    })),



]

