from datetime import datetime

import numpy as np
from scipy.stats import norm

from . import utility


'''
    TODO: :
        1. 
'''

'''
    TODO: refactoring:
        1. no private functions should have var=var arguments
            defaults handled by outward facing functions
'''

class Model:
    home_team = None
    away_team = None
    neutral_site = False
    dist_home_team_score = None
    dist_away_team_score = None
    total = None
    diff = None
    home_field = 0.0

    def __init__(self, home_field = None, neutral_site=False):
        '''
            TODO: if home_field is not None, add logic to ensure home_field:
                1. is a float
                2. is >= 0
            TODO: add logic to ensure neutral_site:
                1. is a bool
        '''
        if home_field is not None and not neutral_site:
            self.home_field = home_field
        if neutral_site:
            self.home_field = 0.0


class PPD_Model(Model):
    weights =  [0.15, 0.35, 0.5]
    def __init__(self, weights=[], home_field=None, neutral_site=False):
        '''
            TODO: if weights, add logic to ensure weights:
                1. is a list or numpy array like
                2. all values >= 0.0
                3. all values sum to 1
        '''
        Model.__init__(self, home_field=home_field, neutral_site=neutral_site)
        if weights:
            self.weights = weights

    def __predict_score(self, home_team_dists, away_team_dists):
        # * Rules for normal distributions
        # * N(m1, v1) + N(m2, v2) = N(m1 + m2, v1 + v2)
        # * N(m1, v1) - N(m2, v2) = N(m1 - m2, v1 - v2)
        # * a*N(m1, v1) = N( a*m1, (a^2)*v1 ) 

        home_team_ppd = ( (home_team_dists['offense'][0] + away_team_dists['defense'][0]) / 2.0, 
                                (home_team_dists['offense'][1] + away_team_dists['defense'][1]) / 4.0 )
        
        away_team_ppd = ( (away_team_dists['offense'][0] + home_team_dists['defense'][0]) / 2.0, 
                                (away_team_dists['offense'][1] + home_team_dists['defense'][1]) / 4.0 )

        dpg = ( (home_team_dists['dpg'][0] + away_team_dists['dpg'][0]) / 2.0, 
                                (home_team_dists['dpg'][1] + away_team_dists['dpg'][1]) / 4.0 )

        # * May not always be self.home_team_score, could be components
        home_team_score = utility.dist_sample_mult(home_team_ppd, dpg, ns=1000000)
        away_team_score = utility.dist_sample_mult(away_team_ppd, dpg, ns=1000000)
        return home_team_score, away_team_score

    def __ppd_dists(self, team_name, drive_data, timeline, predicted_game=None):
        seasons = []
        for i in range(timeline[0], timeline[1] + 1):
            seasons += [i]
        hist_data = drive_data.loc[drive_data['season'].isin(seasons)]
        recent_data = drive_data.loc[drive_data['season'] == seasons[-1]]
        if recent_data.empty:
            recent_data = drive_data.loc[drive_data['season'] == seasons[-2]]            
        current_data = utility.drives_from_recent_games(drive_data, last_games=3, predicted_game=predicted_game)

        drive_dists = {}
        drive_dists['hist'] = self.__calculate_ppd(team_name, hist_data)
        drive_dists['recent'] = self.__calculate_ppd(team_name, recent_data)
        drive_dists['current'] = self.__calculate_ppd(team_name, current_data)
        return drive_dists

    def __drive_scoring(self, team_name, drive_tuple, turn_over=False):
        '''
            TODO: everything:
                1. this code has not been examined for improvement
        '''
        '''
            Consider asking for the next drives results for any change of 
            possession event, not just INT and FUMBLE
        '''
        drive_result = getattr(drive_tuple, "drive_result")
        if drive_result == "TD":
            return 7, getattr(drive_tuple, "offense") == team_name
        elif drive_result == "FG":
            return 3, getattr(drive_tuple, "offense") == team_name
        elif drive_result == "PUNT" or drive_result == "DOWNS" or turn_over:
            return 0, getattr(drive_tuple, "offense") == team_name
        else:
            return drive_result, getattr(drive_tuple, "offense") == team_name

    def __calculate_ppd(self, name, drives_df):
        '''
            TODO: everything:
                1. this code has not been examined for improvement
        '''
        #TODO: add logic to figure out if a game ended or quarter changed for turnover calcs
        turn_over = False
        offense_results = []
        defense_results = []
        drives_per_game = []
        game_drives = 0
        game = -1
        for drive in drives_df.itertuples(index=True, name='Drive'):
            this_game = getattr(drive, "game_id")
            if game == this_game:
                game_drives += 1
            else:
                drives_per_game +=[game_drives]
                game = this_game
                game_drives = 1
            drive_points, on_offense = self.__drive_scoring(name, drive, turn_over=turn_over)
            if type(drive_points) == str:
                turn_over = True

            elif on_offense and not turn_over:
                offense_results += [drive_points]
                turn_over = False

            elif not on_offense and not turn_over:
                defense_results += [drive_points]
                turn_over = False

            elif not on_offense and turn_over:
                offense_results += [-1 * drive_points]
                defense_results += [drive_points]
                turn_over = False

            elif on_offense and turn_over:
                defense_results += [-1 * drive_points]
                offense_results += [drive_points]
                turn_over = False

        np_offense_results = np.array(offense_results)
        np_defense_results = np.array(defense_results)
        np_drives_per_game = np.array(drives_per_game)

        ppd = {}
        ppd['offense'] = (np.mean(np_offense_results), np.var(np_offense_results))
        ppd['defense'] = (np.mean(np_defense_results), np.var(np_defense_results))
        ppd['dpg'] = (np.mean(np_drives_per_game), np.var(np_drives_per_game))

        return ppd

    def predict(self, home_team, away_team, timeline=[datetime.now().year - 4, datetime.now().year - 1], predicted_game=None):
        '''
            TODO: input checking:
                1. home_team and away_team are instinces of Team class
                2. timeline is correct
        '''
        
        self.home_team = home_team
        self.away_team = away_team

        # self.home_team.get_drive_data(timeline=timeline)
        self.home_team.get_drive_data(timeline=[2005, 2018]) # * for model analysis only

        # self.away_team.get_drive_data(timeline=timeline)
        self.away_team.get_drive_data(timeline=[2005, 2018]) # * for model analysis only

        home_team_drive_dists = self.__ppd_dists(self.home_team.name, self.home_team.drive_data, timeline, predicted_game=predicted_game)
        away_team_drive_dists = self.__ppd_dists(self.away_team.name, self.away_team.drive_data, timeline, predicted_game=predicted_game)

        home_score_hist, away_score_hist = self.__predict_score(home_team_drive_dists['hist'], away_team_drive_dists['hist'])
        home_score_recent, away_score_recent = self.__predict_score(home_team_drive_dists['recent'], away_team_drive_dists['recent'])
        home_score_current, away_score_current = self.__predict_score(home_team_drive_dists['current'], away_team_drive_dists['current'])
        
        home_score_mean = self.weights[0] * home_score_hist[0] + self.weights[1] * home_score_recent[0] + self.weights[2] * home_score_current[0]
        home_score_var =(self.weights[0] ** 2.0) * home_score_hist[1] + (self.weights[1] ** 2.0) * home_score_recent[1] + (self.weights[2] ** 2.0) * home_score_current[1]

        away_score_mean = self.weights[0] * away_score_hist[0] + self.weights[1] * away_score_recent[0] + self.weights[2] * away_score_current[0]
        away_score_var =(self.weights[0] ** 2.0) * away_score_hist[1] + (self.weights[1] ** 2.0) * away_score_recent[1] + (self.weights[2] ** 2.0) * away_score_current[1]

        self.dist_home_team_score = (home_score_mean, home_score_var)
        self.dist_away_team_score = (away_score_mean, away_score_var)

        self.total = (home_score_mean + away_score_mean, home_score_var + away_score_var)
        self.diff = (home_score_mean + self.home_field - away_score_mean, home_score_var + away_score_var)
        return self.total, self.diff
