# -*- coding: utf-8 -*-
"""
Created on Sat Apr  1 07:33:08 2023

@author: Local User
"""
from datetime import datetime, timedelta

import pandas as pd 
import pytz
import numpy as np
import statsapi

def convert_odds(odds, second_odds = None):
    
    if (odds > 0) and (second_odds == None):
        
        return 100 / (odds + 100)
    
    if (odds < 0) and (second_odds == None):
        
        return abs(odds) / (abs(odds) + 100)
    
    if odds > 0 and second_odds <= 0:
       return (100 / (odds + 100)) * (abs(second_odds) / (abs(second_odds) + 100))
        
    if odds < 0 and second_odds <= 0:
        return (abs(odds) / (abs(odds) + 100)) * (abs(second_odds) / (abs(second_odds) + 100))
    
    if odds < 0 and second_odds >= 0:
        return (abs(odds) / (abs(odds) + 100)) * (100 / (second_odds + 100))
    
    if odds >0 and second_odds > 0:
        
        return (100 / (odds + 100)) * (100 / (second_odds + 100))
    
def convert_probability(probability):

    probability = round(probability,2)
    
    if probability == 1.0:
        probability = 0.75
    
    decimal = 1 / (probability / 1)

    if probability >= .50:
        
        odds = -100 / (decimal -1)
        return odds
        
    if probability < .50:
        
        odds = (decimal - 1) * 100
        return odds
    
def seconds_to_hours(seconds):
    
    minutes = (seconds / 60) / 60
    return minutes

Data = pd.read_csv("Full_MLB_Data_With_Odds.csv")
Data['game_datetime'] = pd.to_datetime(Data['game_datetime'].values).tz_convert(tz = pytz.timezone('US/Central'))
Data['odds_timestamp'] = pd.to_datetime(Data['odds_timestamp'].values).tz_convert(tz = pytz.timezone('US/Central'))
Data = Data.sort_values(by = 'odds_timestamp')
Data = Data.rename(columns = {'point_odds_source':'odds_source'})

Useful_Data = Data[['game_id','game_datetime', 'game_date','odds_timestamp','home_name','away_name', 'winning_team','losing_team','odds_source','event_id','market','name_0','price_0','point_0','name_1','price_1','point_1']]

Box_Score_DataFrame = pd.read_csv('1998_2022_Box_Scores.csv')
Box_Score_DataFrame_Original = Box_Score_DataFrame.copy()

Big_Game_Data = pd.read_csv('1998_2022_Each_MLB_Game.csv').drop_duplicates('game_id')

game_data = Data.copy()
game_data['realized_total'] = game_data['home_score'] + game_data['away_score']

game_data = game_data[game_data['odds_source'] == 'lowvig'] # or any book you choose
game_data = game_data[game_data['market'] == 'h2h']

game_data = game_data[game_data['game_type'] == 'R']

Team_Pairings_DataFrame = pd.read_csv('Teams_and_IDs.csv').set_index('Team_ID')

dates = pd.to_datetime(pd.date_range(start = game_data['game_datetime'].min().strftime("%Y-%m-%d"), end = game_data['game_datetime'].max().strftime("%Y-%m-%d")).strftime('%Y-%m-%d'))
dates = dates[(dates.isin(game_data['game_date'])) & (dates.year != 2026)]

#####


def Return_Prediction(Home_Team, Away_Team):
        
    Full_Bet_DataFrame = pd.DataFrame([])
    

    Game_Selection = game_data[game_data['home_name'].str.contains(Home_Team) | game_data['away_name'].str.contains(Home_Team) | game_data['home_name'].str.contains(Away_Team) | game_data['away_name'].str.contains(Home_Team)]

    
    home_team = Home_Team
    away_team = Away_Team
    
    Team_Selections = []
    
    Team_Selections.append([home_team, away_team])
    
    years = [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022]
    
    Prediction_List = []
    
    for year in years:
        
        Double_Team_Useful_Metrics = pd.DataFrame([])
    
        for team_name in Team_Selections[0]:
        
            Single_Team_Home = Big_Game_Data[Big_Game_Data['home_name'].str.contains(team_name)]
            Single_Team_Away = Big_Game_Data[Big_Game_Data['away_name'].str.contains(team_name)]
            
            # Get games played for a team
            
            Single_Team_Total = pd.concat([Single_Team_Home, Single_Team_Away], axis = 0).drop_duplicates(subset = ['game_date'], keep = 'last').sort_values(by = 'game_date')
            Single_Team_Total = Single_Team_Total[Single_Team_Total['status'] == 'Final'].reset_index(drop = True)
            
            Single_Team_Total_Original = Single_Team_Total.copy()
            
            # Determine how far into the season you want to go
            
            Single_Team_Total = Single_Team_Total[(Single_Team_Total['game_date'] >= f"{year}-01-01") & (Single_Team_Total['game_date'] <= f"{year+3}-01-01")]
            
            # For each of the played games, get the score stats
            
            Single_Team_Historical_DataFrame = Box_Score_DataFrame_Original[Box_Score_DataFrame_Original['game_id'].isin(Single_Team_Total['game_id'])].reset_index(drop = True).copy().sort_values(by = 'game_date', ascending = True)
            
            if len(Single_Team_Historical_DataFrame) == 0:
                continue
            
            else:
                
                Single_Team_Historical_DataFrame = Single_Team_Historical_DataFrame.set_index('game_date')
                
                Single_Team_Home_Games = Single_Team_Historical_DataFrame[Single_Team_Historical_DataFrame['home_team_id'] == Team_Pairings_DataFrame.index[Team_Pairings_DataFrame['Team_Name'] == team_name][0]].dropna()
                
                # we replace runs with rbi, rbi is "earned" and thus more reflective of skill
                
                Single_Team_Offensive = Single_Team_Home_Games[Single_Team_Home_Games.columns[Single_Team_Home_Games.columns.str.contains("batting")]]
                Single_Team_Offensive = Single_Team_Offensive[Single_Team_Offensive.columns[~Single_Team_Offensive.columns.isin(["batting_runs","batting_avg","batting_obp","batting_ops", "batting_doubles", "batting_triples","batting_leftOnBase", "batting_baseOnBalls", "batting_strikeOuts", "batting_atBats"])]]
    
                Single_Team_Defensive = Single_Team_Home_Games[Single_Team_Home_Games.columns[Single_Team_Home_Games.columns.str.contains("pitching")]]
                Single_Team_Defensive = Single_Team_Defensive[Single_Team_Defensive.columns[~Single_Team_Defensive.columns.isin(["pitching_runs","pitching_pitchesThrown","pitching_strikes","pitching_numberOfPitches", "pitching_doubles", "pitching_triples", "pitching_inningsPitched", "pitching_atBats", "pitching_era", "pitching_baseOnBalls","pitching_earnedRuns"])]]      
           
                Runs_Scored = Single_Team_Offensive['batting_rbi'].sum()
                Runs_Allowed = Single_Team_Defensive['pitching_rbi'].sum()
                
                Run_Differential = Runs_Scored - Runs_Allowed
                
                Win_Rate = len(Single_Team_Total[(Single_Team_Total['winning_team'] == team_name) & (Single_Team_Total['game_date'].isin(Single_Team_Offensive.index))]) / len(Single_Team_Offensive)
                
                Single_Team_Useful_Metrics = pd.DataFrame(data = [Run_Differential, Win_Rate]).rename(index = {0:'run_differential', 1:'win_rate'}).T
                Single_Team_Useful_Metrics['team_name'] = team_name
                Single_Team_Useful_Metrics['custom_score'] = Single_Team_Useful_Metrics['run_differential']#(Single_Team_Useful_Metrics['hits_per_game'] + Single_Team_Useful_Metrics['runs_per_game'] + Single_Team_Useful_Metrics['run_differential'])
                
                Single_Team_Useful_Metrics = Single_Team_Useful_Metrics.set_index('team_name')
                
                Double_Team_Useful_Metrics = pd.concat([Double_Team_Useful_Metrics, Single_Team_Useful_Metrics], axis = 0)
                       
        Score_Spread = Double_Team_Useful_Metrics['custom_score'].max() - Double_Team_Useful_Metrics['custom_score'].min()
       
        Winner_Prediction = Double_Team_Useful_Metrics.index[Double_Team_Useful_Metrics['custom_score'] == Double_Team_Useful_Metrics['custom_score'].max()][0]    
        
        Prediction_List.append(Winner_Prediction)
        
    Prediction_DataFrame = pd.DataFrame(Prediction_List).rename(columns = {0:'Prediction'})
    
    Most_Frequent_Prediction = Prediction_DataFrame['Prediction'].mode()[0]
        
    Prediction_Frequency = len(Prediction_DataFrame[Prediction_DataFrame['Prediction'] == Most_Frequent_Prediction]) / len(Prediction_DataFrame)
    
    Theoretical_Odds = convert_probability(Prediction_Frequency)
    
    return print(f"Prediction: {Most_Frequent_Prediction}, Theo Odds: {Theoretical_Odds}, Implied Probability: {round(Prediction_Frequency * 100, 2)}%")

Return_Prediction(Home_Team = 'Houston Astros', Away_Team = 'Chicago White Sox')

Schedule = statsapi.schedule(start_date = datetime.today().strftime("%Y-%m-%d"), end_date = datetime.today().strftime("%Y-%m-%d"))

for game in Schedule:
    
    Return_Prediction(Home_Team = game['home_name'], Away_Team = game['away_name'])

