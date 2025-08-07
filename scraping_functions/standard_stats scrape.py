from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

teamLinks = ['https://fbref.com/en/comps/9/stats/Premier-League-Stats']

# create empty dictionary with attributes
players_info = {'name': [],
                'team': [],
                'season': [],
                'competition': [], 
                'nation': [], 
                'age': [], 
                'position': [], 
                'matches': [],
                'minutes': [],
                'goals': [], 
                'assists': [], 
                'xG': [], 
                'xGA': [] }

for link in teamLinks:
    options = Options()
    driver = webdriver.Chrome(options=options)
    driver.get(link)
    time.sleep(0.5)
    source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(source, 'lxml')

    players=soup.find('div', id='div_stats_standard').find('tbody').find_all('tr')

    for player in players:

        player_data = {}

        if 'class' in player.attrs and 'thead' in player['class']:
            continue

        # get the name
        name = player.find('td', {'data-stat': 'player'}).a.text.strip()
        player_data['name']=name

        # get the team
        team = player.find('td', {'data-stat': 'team'}).a.text.strip()
        player_data['team']=team

        # get the season
        player_data['season']='24/25'

        # get the competition
        player_data['competition']='Premier League'

        # get the nation
        try:
            nation = player.find('td', {'data-stat': 'nationality'}).a.span.text.split(' ')[1].strip()
        except:
            nation=None
        player_data['nation']=nation

        # get the age
        age = player.find('td', {'data-stat': 'age'}).text.strip()
        player_data['age']=age

        # get the position 
        position = player.find('td', {'data-stat': 'position'}).text.strip()
        player_data['position']=position

        # get the matches played 
        matches = player.find('td', {'data-stat': 'games'}).text.strip()
        player_data['matches']=matches

        # get the minutes played 
        minutes = player.find('td', {'data-stat': 'minutes'}).text.strip()
        player_data['minutes']=minutes

        # get the goals
        goals = player.find('td', {'data-stat': 'goals'}).text.strip()
        player_data['goals']=goals

        # get the assists
        assists = player.find('td', {'data-stat': 'assists'}).text.strip()
        player_data['assists']=assists

        # get the xG
        xG = player.find('td', {'data-stat': 'xg'}).text.strip()
        player_data['xG']=xG

        # get the xG - assists
        xG_assists = player.find('td', {'data-stat': 'xg_assist'}).text.strip()
        player_data['xGA']=xG_assists
        
        # put all the information in the dictionary
        for key in players_info:
            players_info[key].append(player_data.get(key, None))
        

import pandas as pd

# create the data frame to display the data in row/col
df=pd.DataFrame(players_info)

# pd.set_option('display.max_rows', None)
print(df)

# create a csv file
df.to_csv('Prem player_standard_stats.csv', index=False)

