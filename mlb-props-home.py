# -*- coding: utf-8 -*-
"""
Created on Sat Apr 15 14:20:12 2023

@author: Local User
"""

import pandas as pd
import statsapi
from statsapi import player_stat_data
import requests
from datetime import datetime, timedelta
import numpy as np
import math

Big_Game_Data = pd.read_csv('1998_2022_Each_MLB_Game.csv').drop_duplicates('game_id')
Box_Score_DataFrame = pd.read_csv('1998_2022_Box_Scores.csv')
Teams_and_IDs = pd.read_csv("Teams_and_IDs.csv")
Historical_Games_Played = pd.read_csv("MLB_Historical_Games_Played.csv")
Player_Positions = pd.read_csv("MLB_Player_Positions.csv")

def Team_To_ID(team_name):

    
    team_id = Teams_and_IDs["Team_ID"][Teams_and_IDs['Team_Name'] == team_name].iloc[0]

    return team_id

def ID_To_Team(team_id):
    
    team_name = Teams_and_IDs["Team_Name"][Teams_and_IDs['Team_ID'] == team_id].iloc[0]
    
    return team_name

def Player_to_ID(player_name):
    
    player_id = Teams_and_IDs[Teams_and_IDs["Team_Name"] == player_name]["Team_ID"].iloc[0]
    
    return player_id

roster_types = pd.json_normalize(statsapi.meta(type="rosterTypes"))

roster_type = "allTime"

All_Teams_Data = []

for team_id in Teams_and_IDs['Team_ID']:

    roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType={roster_type}"

    response = requests.get(roster_url)

    roster_data = response.json()['roster']

    for player in roster_data:
        
        Player_Name = player['person']['fullName']
        Player_ID = player['person']['id']
        
        Player_Dictionary = {"Team_ID":team_id,"Player Name":Player_Name, "Player ID":Player_ID}
        
        All_Teams_Data.append(Player_Dictionary)

All_Teams_DataFrame = pd.DataFrame(All_Teams_Data)

# =============================================================================
# Calculation
# =============================================================================

Pitching_Historical_Matchup_List = []
Batting_Historical_Result_List = []

completed_teams = []

## if stopped

for unique_team in Teams_and_IDs["Team_Name"]:
    
    if (unique_team in completed_teams) == True:
        
        continue
    
    completed_teams.append(unique_team)
    
    start = datetime.now()

    Team_One = Team_To_ID(unique_team)

    Historical_Schedule_List = []
    
    Start_Date = "2018-03-30"
    End_Date = "2023-04-19"
    
    date_range = (pd.date_range(start=Start_Date, end=End_Date, freq='D'))
    num_iterations = math.ceil(len(date_range) / 200)
    
    
    for historical_period in range(num_iterations):
 
        try:
            Historical_Schedule = statsapi.schedule(start_date=Start_Date, end_date=(End_Date), team=Team_One)
            # Historical_Schedule = statsapi.schedule(start_date=Start_Date, end_date=(pd.to_datetime(Start_Date) + timedelta(days = 200)).strftime("%Y-%m-%d"), team=Team_One)
        except Exception:
            continue
        
        Historical_Schedule_List.append(Historical_Schedule)
        
        Start_Date = (pd.to_datetime(Start_Date) + timedelta(days = 201)).strftime("%Y-%m-%d")

    
    for historical_schedule_group in Historical_Schedule_List:
        
        historical_schedule = historical_schedule_group
        
        for historical_game in historical_schedule:
            
            # historical_game = Historical_Schedule[Historical_Schedule.index == historical_game]
            
            pitching_stats_list = []
            batting_stats_list = []
            
            historical_game_id = historical_game["game_id"]#.iloc[0]
            
            try:
                historical_game_boxscore = statsapi.boxscore_data(historical_game_id)
            except Exception:
                continue                
            
            historical_game_date = historical_game["game_date"]#.iloc[0]
            
            historical_game_venue_id = historical_game["venue_id"]
            
            if historical_game["home_id"] == Team_One:
                
                offense_side ="home"
                defense_side ="away"
                
                offense_key = historical_game["home_id"]
                defense_key = historical_game["away_id"]
                
            elif historical_game["away_id"] == Team_One:
                
                offense_side = "away"
                defense_side ="home"
                
                offense_key = historical_game["away_id"]
                defense_key = historical_game["home_id"]
        
            batter_ids = historical_game_boxscore[offense_side]["batters"]
            batter_players_object = historical_game_boxscore[offense_side]["players"]
            
            for batter_id in list(batter_ids):
                
                batter_player = batter_players_object[f"ID{batter_id}"]
                
                batter_name = batter_player["person"]["fullName"]
                batter_stats = batter_player["stats"]["batting"]
                
                if len(batter_stats) < 1:
                    
                    continue
                
                batter_dictionary = {"Name":batter_name,"Batting":batter_stats}
                batting_stats_list.append(batter_dictionary)   
            
            pitcher_ids = historical_game_boxscore[defense_side]["pitchers"]
            pitcher_players_object = historical_game_boxscore[defense_side]["players"]
            
            for pitcher_id in list(pitcher_ids):
                
                pitcher_player = pitcher_players_object[f"ID{pitcher_id}"]
                
                pitcher_name = pitcher_player["person"]["fullName"]
                pitcher_stats = pitcher_player["stats"]["pitching"]
                
                if len(pitcher_stats) < 1:
                    
                    continue
                
                pitcher_dictionary = {"Name":pitcher_name,"Pitching":pitcher_stats}
                pitching_stats_list.append(pitcher_dictionary)   
            
            
            '''# Stat Builder #######################################################################'''
            
            # gets what the batters did that game
            
            Batter_Historical_List = [] 
            Batter_Historical_Game_Stat_List = []
            
            for batter in batting_stats_list:
            
                batter_historical_stats = []
            
                batter_name = batter["Name"]
                
                batter_id_object = All_Teams_DataFrame[All_Teams_DataFrame["Player Name"] == batter_name]
                
                if len(batter_id_object) < 1:
                    continue
                
                batter_id = batter_id_object["Player ID"].iloc[0]
                batter_team = batter_id_object["Team_ID"].iloc[0]
                
                try:
                    batter_data = statsapi.player_stat_data(personId = batter_id, group="hitting", type="yearByYear", sportId=1)["stats"]
                except Exception:
                    continue

                
                for batter_historical_year in batter_data:
                    
                    if batter_historical_year["season"] < pd.to_datetime(historical_game_date).strftime("%Y"):
                        
                        if (int(batter_historical_year["season"]) - int(pd.to_datetime(historical_game_date).strftime("%Y"))) == -1:
                        
                            batter_stats = pd.DataFrame([batter_historical_year["stats"]])
                            batter_stats["name"] = batter_name
                            
                            batter_historical_stats.append(batter_stats)
                            
                        else:
                            continue
                    else:
                        continue
        
                if len(batter_historical_stats) < 1:
                    continue
                
                batter_stats_of_game = batter["Batting"]
                
                if len(batter_stats_of_game) < 1:
                    continue
                
                batter_historical_stats_dataframe = pd.concat(batter_historical_stats)
                
                if len(batter_historical_stats_dataframe.columns) < 21:
                    
                    continue
        
                
                games_played = batter_historical_stats_dataframe["gamesPlayed"].sum()
                
                #

                batter_historical_dictionary = {
                                                "gamesPlayed": games_played,
                                                "groundOuts": batter_historical_stats_dataframe["groundOuts"].sum() / games_played,
                                                "airOuts": batter_historical_stats_dataframe["airOuts"].sum() / games_played,
                                                "runs": batter_historical_stats_dataframe["runs"].sum() / games_played,
                                                "doubles": batter_historical_stats_dataframe["doubles"].sum() / games_played,
                                                "triples": batter_historical_stats_dataframe["triples"].sum() / games_played,
                                                "homeRuns": batter_historical_stats_dataframe["homeRuns"].sum() / games_played,
                                                "strikeOuts": batter_historical_stats_dataframe["strikeOuts"].sum() / games_played,
                                                "baseOnBalls": batter_historical_stats_dataframe["baseOnBalls"].sum() / games_played,
                                                "hits": batter_historical_stats_dataframe["hits"].sum() / games_played,
                                                "hitByPitch": batter_historical_stats_dataframe["hitByPitch"].sum() / games_played,
                                                "atBats": batter_historical_stats_dataframe["atBats"].sum() / games_played,
                                                "caughtStealing": batter_historical_stats_dataframe["caughtStealing"].sum() / games_played,
                                                "stolenBases": batter_historical_stats_dataframe["stolenBases"].sum() / games_played,
                                                "numberOfPitches": batter_historical_stats_dataframe["numberOfPitches"].sum() / games_played,
                                                "plateAppearances": batter_historical_stats_dataframe["plateAppearances"].sum() / games_played,
                                                "totalBases": batter_historical_stats_dataframe["totalBases"].sum() / games_played,
                                                "rbi": batter_historical_stats_dataframe["rbi"].sum() / games_played,
                                                "leftOnBase": batter_historical_stats_dataframe["leftOnBase"].sum() / games_played,
                                                "sacBunts": batter_historical_stats_dataframe["sacBunts"].sum() / games_played,
                                                "sacFlies": batter_historical_stats_dataframe["sacFlies"].sum() / games_played,
                                                "venue" : historical_game_venue_id,
                                                
                                                "hit_recorded" : pd.Series(batter_stats_of_game['hits'] > 0).astype(int).iloc[0],
                                                "home_run_recorded" : pd.Series(batter_stats_of_game['homeRuns'] > 0).astype(int).iloc[0],
                                                "rbi_recorded" : pd.Series(batter_stats_of_game['rbi'] > 0).astype(int).iloc[0],
                                                "run_recorded" : pd.Series(batter_stats_of_game['runs'] > 0).astype(int).iloc[0],
                                                "stolen_base_recorded" : pd.Series(batter_stats_of_game['stolenBases'] > 0).astype(int).iloc[0],
                                                "double_recorded" : pd.Series(batter_stats_of_game['doubles'] > 0).astype(int).iloc[0],
                                                "triple_recorded" : pd.Series(batter_stats_of_game['triples'] > 0).astype(int).iloc[0],
                                                "strikeout_recorded" : pd.Series(batter_stats_of_game['strikeOuts'] > 0).astype(int).iloc[0],
                                                "name" : batter_name,
                                                "Game_ID" : historical_game_id,
                                                "batter_id" : batter_id

                                                }


                batter_historical_average_dataframe = pd.DataFrame([batter_historical_dictionary])
                Batter_Historical_List.append(batter_historical_average_dataframe)
                
            
            ####
            
            
            Pitcher_Historical_List = []
            
            for pitcher in pitching_stats_list:
                
                pitcher_historical_stats = []
                
                pitcher_name = pitcher["Name"]
                
                pitcher_id_object = All_Teams_DataFrame[All_Teams_DataFrame["Player Name"] == pitcher_name] 
                
                if len(pitcher_id_object) < 1:
                    continue
                
                pitcher_id = pitcher_id_object["Player ID"].iloc[0]
                pitcher_team = pitcher_id_object["Team_ID"].iloc[0]
                
                try:
                    pitcher_data = statsapi.player_stat_data(personId = pitcher_id, group="pitching", type="yearByYear", sportId=1)["stats"]
                except Exception:
                    continue

                
                for pitcher_historical_year in pitcher_data:
                    
                    if pitcher_historical_year["season"] < pd.to_datetime(historical_game_date).strftime("%Y"):
                        
                        
                        if (int(pitcher_historical_year["season"]) - int(pd.to_datetime(historical_game_date).strftime("%Y"))) == -1:
                                            
                            pitcher_stats = pd.DataFrame([pitcher_historical_year["stats"]])
                            pitcher_stats["name"] = pitcher_name
                            
                            pitcher_historical_stats.append(pitcher_stats)
                            
                        else:
                            
                            continue
        
            
                if len(pitcher_historical_stats) < 1:
                    continue
                
                pitcher_stats_of_game = pitcher["Pitching"]
                
                if len(pitcher_stats_of_game) < 1:
                    
                    continue
                        
                pitcher_historical_stats_dataframe = pd.concat(pitcher_historical_stats)
                
                games_played = pitcher_historical_stats_dataframe["gamesPitched"].sum()
                at_bats = pitcher_historical_stats_dataframe["atBats"].sum()
                
                at_bats_per_game = at_bats / games_played
                               

                pitcher_historical_dictionary = {
                    'gamesPlayed': games_played,
                  'runs': pitcher_historical_stats_dataframe["runs"].sum() / games_played,
                  'doubles': pitcher_historical_stats_dataframe["doubles"].sum() / games_played,
                  'triples': pitcher_historical_stats_dataframe["triples"].sum() / games_played,
                  'homeRuns': pitcher_historical_stats_dataframe["homeRuns"].sum() / games_played,
                  'strikeOuts': pitcher_historical_stats_dataframe["strikeOuts"].sum() / games_played,
                  'baseOnBalls': pitcher_historical_stats_dataframe["baseOnBalls"].sum() / games_played,
                  'hits': pitcher_historical_stats_dataframe["hitByPitch"].sum() / games_played,
                  'hitByPitch': pitcher_historical_stats_dataframe["hitByPitch"].sum() / games_played,
                  'atBats': at_bats_per_game,
                  'caughtStealing': pitcher_historical_stats_dataframe["caughtStealing"].sum() / games_played,
                  'stolenBases': pitcher_historical_stats_dataframe["stolenBases"].sum() / games_played,
                  'numberOfPitches': pitcher_historical_stats_dataframe["numberOfPitches"].sum() / games_played,
                  'era': pitcher_historical_stats_dataframe["era"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'inningsPitched': pitcher_historical_stats_dataframe["inningsPitched"].replace([".---", "-.--"], np.nan).astype(float).sum() / games_played,
                  'saves': pitcher_historical_stats_dataframe["saves"].sum() / games_played,
                  'saveOpportunities': pitcher_historical_stats_dataframe["saveOpportunities"].sum() / games_played,
                  'holds': pitcher_historical_stats_dataframe["holds"].sum() / games_played,
                  'blownSaves': pitcher_historical_stats_dataframe["blownSaves"].sum() / games_played,
                  'earnedRuns': pitcher_historical_stats_dataframe["earnedRuns"].sum() / games_played,
                  'battersFaced': pitcher_historical_stats_dataframe["battersFaced"].sum() / games_played,
                  'outs': pitcher_historical_stats_dataframe["outs"].sum() / games_played,
                  'strikes': pitcher_historical_stats_dataframe["strikes"].sum() / games_played,
                  'strikePercentage': pitcher_historical_stats_dataframe["strikePercentage"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'wildPitches': pitcher_historical_stats_dataframe["wildPitches"].sum() / games_played,
                  'totalBases': pitcher_historical_stats_dataframe["totalBases"].sum() / games_played,
                  'winPercentage': pitcher_historical_stats_dataframe["winPercentage"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'pitchesPerInning': pitcher_historical_stats_dataframe["pitchesPerInning"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'gamesFinished': pitcher_historical_stats_dataframe["gamesFinished"].sum(),
                  'strikeoutsPer9Inn': pitcher_historical_stats_dataframe["strikeoutsPer9Inn"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'walksPer9Inn': pitcher_historical_stats_dataframe["walksPer9Inn"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'hitsPer9Inn': pitcher_historical_stats_dataframe["hitsPer9Inn"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'runsScoredPer9': pitcher_historical_stats_dataframe["runsScoredPer9"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'homeRunsPer9': pitcher_historical_stats_dataframe["homeRunsPer9"].replace([".---", "-.--"], np.nan).astype(float).mean(),
                  'inheritedRunners': pitcher_historical_stats_dataframe["inheritedRunnersScored"].sum() / games_played,
                  'inheritedRunnersScored': pitcher_historical_stats_dataframe["sacFlies"].sum() / games_played,
                  'sacBunts': pitcher_historical_stats_dataframe["sacBunts"].sum() / games_played,
                  'sacFlies': pitcher_historical_stats_dataframe["sacFlies"].sum() / games_played,
                  "venue" : historical_game_venue_id,
                  'name': pitcher_name,
                  "Game_ID" : historical_game_id,
                  "pitcher_id": pitcher_id
                  }

                pitcher_historical_average_dataframe = pd.DataFrame([pitcher_historical_dictionary])
                Pitcher_Historical_List.append(pitcher_historical_average_dataframe)
        
            if (len(Pitcher_Historical_List) < 1) or (len(Batter_Historical_List) < 1):
        
                continue
            
                
            Pitching_Team_Historicals = pd.concat(Pitcher_Historical_List)
            
            Batter_Performance_DataFrame = pd.concat(Batter_Historical_List)

            Pitching_Historical_Matchup_List.append(Pitching_Team_Historicals)
            Batting_Historical_Result_List.append(Batter_Performance_DataFrame)
    
    end = datetime.now()
    print(f"{end - start } Completed 1 Team") 
       
# =============================================================================
# End of Calculation
# =============================================================================

def Format_Data():

    Pitcher_History = pd.concat(Pitching_Historical_Matchup_List)#.drop_duplicates(["pitcher_id","Game_ID"])#.fillna(0)#.drop_duplicates()
    Batter_Performance = pd.concat(Batting_Historical_Result_List)#.drop_duplicates(["name","Game_ID"])#.drop("note", axis = 1)
    
    Pitchers = list(Pitcher_History["name"].drop_duplicates())
    Batters = list(Batter_Performance["name"].drop_duplicates())
    
    Game_Submission_List = []
    
    for unique_batter in Batters:
        
        Target_Player = unique_batter
        
        Target_Batter_Games = Batter_Performance[Batter_Performance["name"] == Target_Player]
        
        Pitching_Games_With_Batter = Pitcher_History[Pitcher_History["Game_ID"].isin(list(Target_Batter_Games["Game_ID"]))]
        
        for batter_game in list(Pitching_Games_With_Batter["Game_ID"]):
            
            batting_data = Batter_Performance[(Batter_Performance["Game_ID"] == batter_game) & (Batter_Performance["name"] == unique_batter)]
            
            pitching_data = Pitcher_History[Pitcher_History["Game_ID"] == batter_game]
            
            for unique_pitcher in list(pitching_data["name"]):
        
                Target_Pitcher = unique_pitcher
            
                Games_With_Target_Pitcher = Pitching_Games_With_Batter[(Pitching_Games_With_Batter["name"] == Target_Pitcher) & (Pitching_Games_With_Batter["Game_ID"] == batter_game)]#.sort_values(by = "Game_ID", ascending = True)
                
                Combined_Game = pd.concat([Games_With_Target_Pitcher.add_prefix("pitching_"), batting_data.add_prefix("batting_")], axis = 1)
                
                Game_Submission_List.append(Combined_Game)
    
        
    Final_Game_DataFrame_Original = pd.concat(Game_Submission_List).reset_index(drop = True)#.drop_duplicates(subset = ["pitching_pitcher_id","pitching_Game_ID"]).drop_duplicates(subset = ["batting_batter_id","batting_Game_ID"])
    
    Final_Game_DataFrame = Final_Game_DataFrame_Original.copy().drop_duplicates(subset = ["batting_batter_id","batting_Game_ID"])
    
    print(f"Unique Games: {len(Final_Game_DataFrame['pitching_Game_ID'].drop_duplicates())}")
    Final_Game_DataFrame.to_csv("final_game.csv")
    # Final_Game_DataFrame.to_csv("new_final_game.csv")
    
Format_Data()    
    