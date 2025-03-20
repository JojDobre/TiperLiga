from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, TeamViewSet, LeagueViewSet, MatchViewSet,
    login_view, refresh_token_view, UserProfileViewSet, SocialViewSet, CompetitionViewSet, BetViewSet, 
    BetChallengeViewSet, PlayerViewSet, UserAnalyticsViewSet, SecurityViewSet, TwoFactorViewSet, 
    UserAchievement, UserActivityViewSet, NotificationViewSet, NotificationPreferencesViewSet, ReportViewSet, 
    RoundViewSet, TeamViewSet, PlayerViewSet, UserBettingHistoryViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'bets', BetViewSet, basename='bet')
router.register(r'bet-challenges', BetChallengeViewSet, basename='bet-challenge')
router.register(r'social', SocialViewSet, basename='social')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'players', PlayerViewSet)
router.register(r'user-analytics', UserAnalyticsViewSet, basename='user-analytics')
router.register(r'leagues', LeagueViewSet, basename='league')
router.register(r'competitions', CompetitionViewSet, basename='competition')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', login_view, name='login'),
    path('auth/refresh/', refresh_token_view, name='refresh_token'),    
]