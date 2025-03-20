from rest_framework import serializers
from .models import (
    CustomUser, Team, Venue, League, 
    Competition, Round, Match, Bet
)
from django.utils import timezone
from .achievements import AchievementType, UserAchievement
from .profile import UserProfile, UserSettings, ProfileService
from .social import FriendRequest
from .betting_system import BetChallenge
from .team_management import TeamAnalytics, Player
from .user_activity import UserActivityLog, UserDeviceInfo
from .notifications import NotificationType, UserNotificationPreference, Notification
from .reporting import ReportType, Report
from .team_management import TeamCategory, PlayerPosition, PlayerTransfer
from .user_betting_history import UserBettingHistoryEntry, UserBettingTrend

class UserBettingHistoryEntrySerializer(serializers.ModelSerializer):
    match_details = serializers.SerializerMethodField()

    class Meta:
        model = UserBettingHistoryEntry
        fields = '__all__'

    def get_match_details(self, obj):
        return {
            'home_team': obj.match.home_team.name,
            'away_team': obj.match.away_team.name,
            'competition': obj.match.round.competition.name
        }

class UserBettingTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBettingTrend
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['user']

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        exclude = ['user']


class AchievementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AchievementType
        fields = ['id', 'name', 'description', 'points_reward', 'badge_icon']

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_type = AchievementTypeSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement_type', 'earned_date', 'is_claimed']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'points']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class LeagueSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    competitions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = League
        fields = '__all__'

class CompetitionSerializer(serializers.ModelSerializer):
    leagues = LeagueSerializer(many=True, read_only=True)

    class Meta:
        model = Competition
        fields = '__all__'

class RoundSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)

    class Meta:
        model = Round
        fields = '__all__'

class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    round = RoundSerializer(read_only=True)

    class Meta:
        model = Match
        fields = '__all__'

class BetSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    match = MatchSerializer(read_only=True)

    class Meta:
        model = Bet
        fields = '__all__'
        extra_kwargs = {
            'points_earned': {'read_only': True}
        }

    def validate(self, data):
        # Pridáme validáciu pre bet - napríklad overenie termínu
        match = self.context['match']
        if timezone.now() > match.round.deadline:
            raise serializers.ValidationError("Tipovanie po termíne uzávierky nie je povolené.")
        return data
    
class FriendRequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'status', 'created_at']

class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = '__all__'

class LeagueSerializer(serializers.ModelSerializer):
    competitions = CompetitionSerializer(many=True, read_only=True)

    class Meta:
        model = League
        fields = '__all__'

class BetChallengeSerializer(serializers.ModelSerializer):
    challenger = serializers.PrimaryKeyRelatedField(read_only=True)
    challenged_user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    match = serializers.PrimaryKeyRelatedField(queryset=Match.objects.all())
    
    # Rozšířené informace o zápase
    match_details = serializers.SerializerMethodField()
    
    # Rozšířené informace o uživatelích
    challenger_username = serializers.CharField(source='challenger.username', read_only=True)
    challenged_user_username = serializers.CharField(source='challenged_user.username', read_only=True)

    class Meta:
        model = BetChallenge
        fields = [
            'id', 
            'challenger', 
            'challenger_username',
            'challenged_user', 
            'challenged_user_username',
            'match', 
            'match_details',
            'challenger_prediction_home', 
            'challenger_prediction_away',
            'challenged_user_prediction_home', 
            'challenged_user_prediction_away',
            'stake', 
            'status', 
            'created_at', 
            'updated_at'
        ]
        extra_kwargs = {
            'challenger_prediction_home': {'required': False},
            'challenger_prediction_away': {'required': False},
            'challenged_user_prediction_home': {'required': False},
            'challenged_user_prediction_away': {'required': False},
        }

    def get_match_details(self, obj):
        """
        Vrátí dodatečné detaily o zápase
        """
        return {
            'id': obj.match.id,
            'home_team': obj.match.home_team.name,
            'away_team': obj.match.away_team.name,
            'match_date': obj.match.match_date
        }

    def create(self, validated_data):
        """
        Přepsání metody create pro nastavení challengera
        """
        # Nastaví challengera na aktuálního uživatele
        validated_data['challenger'] = self.context['request'].user
        
        # Kontrola, zda uživatel nevyzývá sám sebe
        if validated_data['challenger'] == validated_data['challenged_user']:
            raise serializers.ValidationError("Nemůžete vyzvat sami sebe")
        
        return super().create(validated_data)

    def validate(self, data):
        """
        Dodatečná validace před vytvořením výzvy
        """
        # Kontrola, zda zápas ještě nezačal
        match = data.get('match')
        if match and match.match_date <= timezone.now():
            raise serializers.ValidationError("Nelze vytvořit výzvu pro zápas, který již začal")
        
        return data
    
class TeamSerializer(serializers.ModelSerializer):
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = '__all__'

    def get_statistics(self, obj):
        return TeamAnalytics.get_team_performance(obj)

class PlayerSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = '__all__'

    def get_age(self, obj):
        return obj.age

    def get_position_name(self, obj):
        return obj.position.name if obj.position else None
    
class UserActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityLog
        fields = ['activity_type', 'timestamp', 'ip_address', 'additional_data']

class UserDeviceInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDeviceInfo
        fields = ['device_type', 'browser', 'os', 'last_login', 'ip_address']

class ReportTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportType
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    report_type = ReportTypeSerializer(read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

class TeamCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamCategory
        fields = '__all__'

class PlayerPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerPosition
        fields = '__all__'

class PlayerTransferSerializer(serializers.ModelSerializer):
    from_team = TeamSerializer(read_only=True)
    to_team = TeamSerializer(read_only=True)

    class Meta:
        model = PlayerTransfer
        fields = '__all__'


class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = '__all__'

class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)

    class Meta:
        model = UserNotificationPreference
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'