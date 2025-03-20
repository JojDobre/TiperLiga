from .models import Bet, Match

class ScoringSystem:
    @staticmethod
    def calculate_bet_points(bet: Bet, match: Match) -> int:
        """
        Výpočet bodov za tip
        """
        points = 0

        # Kontrola, či je zápas ukončený a nie je zrušený
        if not match.home_score or match.is_cancelled:
            return 0

        # Správny výsledok (výhra/prehra/remíza)
        if (match.home_score > match.away_score and bet.home_score_prediction > bet.away_score_prediction) or \
           (match.home_score < match.away_score and bet.home_score_prediction < bet.away_score_prediction) or \
           (match.home_score == match.away_score and bet.home_score_prediction == bet.away_score_prediction):
            points += 3

        # Správny počet gólov pre tím
        if bet.home_score_prediction == match.home_score:
            points += 1
        if bet.away_score_prediction == match.away_score:
            points += 1

        # Správny gólový rozdiel
        predicted_diff = bet.home_score_prediction - bet.away_score_prediction
        actual_diff = match.home_score - match.away_score
        if predicted_diff == actual_diff:
            points += 2

        # Presný výsledok
        if bet.home_score_prediction == match.home_score and bet.away_score_prediction == match.away_score:
            points += 10

        return points

class LeagueScoring:
    @staticmethod
    def update_user_points(league):
        """
        Aktualizácia bodov užívateľov v lige
        """
        # Prejsť všetky zápasy v lige
        for competition in league.competitions.all():
            for round in competition.round_set.all():
                for match in round.match_set.all():
                    # Vyhodnotenie tipov pre daný zápas
                    bets = Bet.objects.filter(match=match)
                    for bet in bets:
                        points = ScoringSystem.calculate_bet_points(bet, match)
                        bet.points_earned = points
                        bet.save()

                        # Aktualizácia celkových bodov užívateľa
                        bet.user.points += points
                        bet.user.save()

    @staticmethod
    def get_league_leaderboard(league):
        """
        Zostavenie rebríčka pre ligu
        """
        # Zozbieranie užívateľov v lige a ich bodov
        users = league.created_by.customuser_set.all().order_by('-points')
        
        leaderboard = []
        for user in users:
            leaderboard.append({
                'user': user.username,
                'points': user.points,
                'rank': len(leaderboard) + 1
            })
        
        return leaderboard