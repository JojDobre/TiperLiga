from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Bet, Match, League

class AchievementType(models.Model):
    """
    Definícia typov achievementov
    """
    name = models.CharField(max_length=100)
    description = models.TextField()
    points_reward = models.IntegerField(default=0)
    badge_icon = models.ImageField(upload_to='achievement_badges/', null=True, blank=True)

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    """
    Uloženie dosiahnutých achievementov pre užívateľa
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    achievement_type = models.ForeignKey(AchievementType, on_delete=models.CASCADE)
    earned_date = models.DateTimeField(auto_now_add=True)
    is_claimed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'achievement_type')

class AchievementService:
    @staticmethod
    def check_and_award_achievements(user):
        """
        Kontrola a udeľovanie achievementov
        """
        achievements_to_award = []

        # Achievement za počet tipov
        total_bets = Bet.objects.filter(user=user).count()
        achievements = [
            (10, 'Začiatočník'),
            (50, 'Skúsený tipér'),
            (100, 'Profesionál'),
            (500, 'Legenda')
        ]

        for bet_count, achievement_name in achievements:
            if total_bets >= bet_count:
                achievement_type, _ = AchievementType.objects.get_or_create(
                    name=achievement_name,
                    defaults={
                        'description': f'Dosiahnutý počet tipov: {bet_count}',
                        'points_reward': bet_count
                    }
                )
                
                # Overenie, či užívateľ už nemá achievement
                existing_achievement = UserAchievement.objects.filter(
                    user=user, 
                    achievement_type=achievement_type
                ).exists()
                
                if not existing_achievement:
                    user_achievement = UserAchievement.objects.create(
                        user=user,
                        achievement_type=achievement_type
                    )
                    achievements_to_award.append(user_achievement)
                    
                    # Pridanie bonusových bodov
                    user.points += achievement_type.points_reward
                    user.save()

        # Achievement za presnosť tipov
        correct_bets = Bet.objects.filter(user=user, points_earned__gt=0).count()
        total_bets = Bet.objects.filter(user=user).count()
        accuracy = (correct_bets / total_bets * 100) if total_bets > 0 else 0

        accuracy_achievements = [
            (50, 'Presný tipér'),
            (70, 'Majster presnosti'),
            (90, 'Prorok')
        ]

        for accuracy_threshold, achievement_name in accuracy_achievements:
            if accuracy >= accuracy_threshold:
                achievement_type, _ = AchievementType.objects.get_or_create(
                    name=achievement_name,
                    defaults={
                        'description': f'Presnosť tipov: {accuracy_threshold}%',
                        'points_reward': int(accuracy)
                    }
                )
                
                existing_achievement = UserAchievement.objects.filter(
                    user=user, 
                    achievement_type=achievement_type
                ).exists()
                
                if not existing_achievement:
                    user_achievement = UserAchievement.objects.create(
                        user=user,
                        achievement_type=achievement_type
                    )
                    achievements_to_award.append(user_achievement)
                    
                    # Pridanie bonusových bodov
                    user.points += achievement_type.points_reward
                    user.save()

        return achievements_to_award

class AchievementSignals:
    @receiver(post_save, sender=Bet)
    def check_bet_achievements(sender, instance, created, **kwargs):
        """
        Signal pre kontrolu achievementov po umiestnení tipu
        """
        if created:
            AchievementService.check_and_award_achievements(instance.user)

class LeagueAchievementService:
    @staticmethod
    def award_league_achievements(league):
        """
        Udeľovanie achievementov na konci ligy
        """
        # Top 3 užívatelia v lige dostanú špeciálne achievementy
        top_users = CustomUser.objects.filter(
            bet__match__round__competition__leagues=league
        ).annotate(
            total_points=models.Sum('bet__points_earned')
        ).order_by('-total_points')[:3]

        league_achievements = [
            ('Víťaz ligy', 100),
            ('Strieborný tipér', 50),
            ('Bronzový tipér', 25)
        ]

        for index, (achievement_name, points_reward) in enumerate(league_achievements, 1):
            if index <= len(top_users):
                user = top_users[index-1]
                achievement_type, _ = AchievementType.objects.get_or_create(
                    name=achievement_name,
                    defaults={
                        'description': f'Top {index} v lige {league.name}',
                        'points_reward': points_reward
                    }
                )
                
                UserAchievement.objects.create(
                    user=user,
                    achievement_type=achievement_type,
                    is_claimed=True
                )
                
                # Pridanie bonusových bodov
                user.points += points_reward
                user.save()