from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator



class CustomUser(AbstractUser):
    USER_ROLES = (
        ('VISITOR', 'Návštevník'),
        ('PLAYER', 'Hráč'),
        ('VIP', 'VIP Admin'),
        ('ADMIN', 'Administrátor')
    )
    role = models.CharField(max_length=10, choices=USER_ROLES, default='VISITOR')
    points = models.IntegerField(default=0)
    
    def __str__(self):
        return self.username

class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    country = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}, {self.city}"

class League(models.Model):
    name = models.CharField(max_length=100)
    season = models.CharField(max_length=20)  # napr. 2024/25
    unique_id = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} ({self.season})"

class Competition(models.Model):
    name = models.CharField(max_length=200)
    leagues = models.ManyToManyField(League, related_name='competitions')
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

class Round(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    deadline = models.DateTimeField()

    def __str__(self):
        return f"{self.competition.name} - {self.name}"

class Match(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True)
    match_date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

class Bet(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    home_score_prediction = models.IntegerField()
    away_score_prediction = models.IntegerField()
    points_earned = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'match')

    def __str__(self):
        return f"{self.user.username} - {self.match}"
    