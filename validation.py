import os
import numpy as np
from git_cfb import fetch_data, model_analysis, model, matchup, team

'''
    TODO: determine the scope of the validation effort:
        * 1. what teams will be involved?
        * 2. what years will be involved?
    TODO: Automate validation
        * 1. get model data for the scope of validation
        * 2. get validation (game) data for the scope of validation
        3. predict each game
            a. differential
            b. total
            c. home score
            d. away score
            e. home score variance (for minimization in later optimizations)
            f. away score variance (for minimization in later optimizations)
        4. Analyze
            a. RMSE values
                i. differential
                ii. total
                iii. home score
                iv. away score
        5. error table for predicted winner
        6. winner probability? (may want to maximize this in later optimizations)
    TODO: Tune the model
        1. set up optimization
        2. maximize % correct winners?
        3. maximize probability of correct winner
        4. minimize standard deviation of predicted scores
        5. drive differential and total probabilities to 0.5 (accuracy)
        6. multiobjective of 5 and 4
'''

# away_team = "Mississippi State"
# home_team = "Ole Miss"

# ppd_model = model.PPD_Model(weights = [0.15, 0.35, 0.5], home_field=0.0)
# game = matchup.Matchup(home_team, away_team, ppd_model, data_dir=data_dir)
# game.analyze(line = 32, over_under=38)

data_dir = os.path.join(os.getcwd(), "data")
model_timeline = [2008, 2018]
data_timeline = [2005, 2018]

game_data = fetch_data.get_game_data(timeline=model_timeline, data_dir=data_dir)
model_data = model_analysis.process_game_data(game_data)
ppd_model = model.PPD_Model(weights = [0.15, 0.35, 0.5], home_field=0.0)
correct_outcome = []
diff_error = []
total_error = []
home_score_error = []
away_score_error = []

# ! Only uncomment to download all team drive data
# for game in model_data.itertuples(name='Game'):
#     home_team = team.Team(game.home_team, data_dir=data_dir)
#     away_team = team.Team(game.away_team, data_dir=data_dir)
#     home_team.get_drive_data(timeline=data_timeline)
#     away_team.get_drive_data(timeline=data_timeline)


for game in model_data.itertuples(name='Game'):
    print("%s v %s" %(game.home_team, game.away_team))
    current_season = game.season
    model_timeline = [current_season - 3, current_season]
    predicted_game = game.id
    pred_game = matchup.Matchup(game.home_team, game.away_team, ppd_model, data_dir=data_dir)
    pred_winner, pred_diff, pred_total, pred_home_points, pred_away_points = pred_game.predict(model_timeline, predicted_game)
    correct_outcome += [pred_winner == game.winner]
    diff_error = [game.point_differential - pred_diff[0]]
    total_error = [game.total_points - pred_total[0]]
    home_score_error = [game.home_points - pred_home_points]
    away_score_error = [game.away_points - pred_away_points]
    print("\npredicted outcome: " + str(correct_outcome[-1]))
    print("differential error: " + str(diff_error[-1]))
    print("total points error: " + str(total_error[-1]))
    print("home points error: " + str(home_score_error[-1]))
    print("away points error: " + str(away_score_error[-1]) + "\n")

perc_correct = (correct_outcome.count(True) / len(correct_outcome)) * 100
np_diff_error = np.array(diff_error)
np_total_error = np.array(total_error)
np_home_score_error = np.array(home_score_error)
np_away_score_error = np.array(away_score_error)

mean_diff_error = np_diff_error.mean()
std_diff_error = np_diff_error.std()
mean_total_error = np_total_error.mean()
std_total_error = np_total_error.std()
mean_home_score_error = np_home_score_error.mean()
std_home_score_error = np_home_score_error.std()
mean_away_score_error = np_away_score_error.mean()
std_away_score_error = np_away_score_error.std()

print("%.2f percent correct" % perc_correct)
print("differential error: %.4f mean and %.4f std dev" %(mean_diff_error, std_diff_error))
print("total points error: %.4f mean and %.4f std dev" %(mean_total_error, std_total_error))
print("home points error: %.4f mean and %.4f std dev" %(mean_home_score_error, std_home_score_error))
print("away points error: %.4f mean and %.4f std dev" %(mean_away_score_error, std_away_score_error))

