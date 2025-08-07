from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

teamLinks = ['https://fbref.com/en/comps/9/keepers/Premier-League-Stats']

# create empty dictionary with attributes
players_info = {'name': [],
                'season': [],
                'competition': [], 
                'nation': [],
                'position': [], 
                'team': [],
                'age': [], 
                'year_born': [],
                'matches': [],
                'starts': [],
                'minutes': [],
                'full_games': [],
                'goals_against': [], 
                'goals_against_per90': [],
                'shots_ontarget_against': [],
                'saves': [],
                'save_percentage': [],
                'wins': [],
                'draws': [],
                'losses': [],
                'clean_sheets': [],
                'clean_sheet_percentage': [],
                'PK_att_against': [],
                'PK_conceded': [],
                'PK_saved': [],
                'PK_save_percentage': []  }

for link in teamLinks:
    options = Options()
    driver = webdriver.Chrome(options=options)
    driver.get(link)
    time.sleep(0.5)
    source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(source, 'lxml')

    players=soup.find('div', id='all_stats_keeper').find('tbody').find_all('tr')

    for player in players:
        
        if 'class' in player.attrs and 'thead' in player['class']:
            continue

        stats = player.find_all('td')

        player_data = {}

        # get the name
        name = stats[0].a.text.strip()
        player_data['name']=name

        # get the season
        player_data['season']='24/25'

        # get the competition
        player_data['competition']='Premier League'

        # get the nation
        try:
            nation = stats[1].a.span.text.split(' ')[1].strip()
        except:
            nation=None
        player_data['nation']=nation

        # get the position 
        position = stats[2].text.strip()
        player_data['position']=position

        # get the team
        team = stats[3].a.text.strip()
        player_data['team']=team

        # get the age
        age = stats[4].text.strip()
        player_data['age']=age

        # get the year born
        year_born = stats[5].text.strip()
        player_data['year_born']=year_born

        # get the matches played 
        matches = stats[6].text.strip()
        player_data['matches']=matches

        # get the starts
        starts = stats[7].text.strip()
        player_data['starts']=starts

        # get the minutes played 
        minutes = stats[8].text.strip()
        player_data['minutes']=minutes

        # get the full games
        full_games = stats[9].text.strip()
        player_data['full_games']=full_games

        # get the goals against
        goals_against = stats[10].text.strip()
        player_data['goals_against']=goals_against

        # get the goals against per 90
        goals_against_per90 = stats[11].text.strip()
        player_data['goals_against_per90']=goals_against_per90

        # get the shots on target against
        shots_ontarget_against = stats[12].text.strip()
        player_data['shots_ontarget_against']=shots_ontarget_against

        # get the saves
        saves = stats[13].text.strip()
        player_data['saves']=saves

        # get the save percentage
        save_percentage = stats[14].text.strip()
        player_data['save_percentage']=save_percentage

        # get the wins
        wins = stats[15].text.strip()
        player_data['wins']=wins

        # get the draws cards
        draws = stats[16].text.strip()
        player_data['draws']=draws

        # get the losses
        losses = stats[17].text.strip()
        player_data['losses']=losses

        # get the clean sheets
        clean_sheets = stats[18].text.strip()
        player_data['clean_sheets']=clean_sheets

        # get the clean sheet percentage
        clean_sheet_percentage = stats[19].text.strip()
        player_data['clean_sheet_percentage']=clean_sheet_percentage

        # get the PKs against
        PK_att_against = stats[20].text.strip()
        player_data['PK_att_against']=PK_att_against

        # get the PKs conceded
        PK_conceded = stats[21].text.strip()
        player_data['PK_conceded']=PK_conceded

        # get the PKs saved
        PK_saved = stats[22].text.strip()
        player_data['PK_saved']=PK_saved

        # get the PK save percentage
        PK_save_percentage = stats[24].text.strip()
        player_data['PK_save_percentage']=PK_save_percentage
        
        # put all the information in the dictionary
        for key in players_info:
            players_info[key].append(player_data.get(key, None))
        

import pandas as pd

# create the data frame to display the data in row/col
df=pd.DataFrame(players_info)

# pd.set_option('display.max_rows', None)
print(df)

# create a csv file
df.to_csv('Prem player_keeper_stats.csv', index=False)

