from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

teamLinks = ['https://fbref.com/en/comps/9/stats/Premier-League-Stats']

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
                'goals': [], 
                'assists': [],
                'G+A': [],
                'non-PK_goals': [],
                'PK_goals': [], 
                'PK_att': [],
                'yellow_cards': [],
                'red_cards': [],
                'xG': [],
                'xG_nonpenalty': [],
                'xGnp+xGA': [],
                'xGA': [],
                'progressive_carries': [],
                'progressive_passes': [], }

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

        # get the age
        full_games = stats[9].text.strip()
        player_data['full_games']=full_games

        # get the goals
        goals = stats[10].text.strip()
        player_data['goals']=goals

        # get the assists
        assists = stats[11].text.strip()
        player_data['assists']=assists

        # get the G+A
        ga = stats[12].text.strip()
        player_data['G+A']=ga

        # get the non PK goals
        nonPK_goals = stats[13].text.strip()
        player_data['non-PK_goals']=nonPK_goals

        # get the PK goals
        PK_goals = stats[14].text.strip()
        player_data['PK_goals']=PK_goals

        # get the PK attempts
        PK_att = stats[15].text.strip()
        player_data['PK_att']=PK_att

        # get the yellow cards
        yellow_cards = stats[16].text.strip()
        player_data['yellow_cards']=yellow_cards

        # get the age
        red_cards = stats[17].text.strip()
        player_data['red_cards']=red_cards

        # get the xG
        xG = stats[18].text.strip()
        player_data['xG']=xG

        # get the non penalty xG
        xG_nonpenalty = stats[19].text.strip()
        player_data['xG_nonpenalty']=xG_nonpenalty

        # get the xG - assists
        xG_assists = stats[20].text.strip()
        player_data['xGA']=xG_assists

        # get the xGnp + xGA
        xGnp_A = stats[21].text.strip()
        player_data['xGnp+xGA']=xGnp_A

        # get the progressive carries
        progressive_carries = stats[22].text.strip()
        player_data['progressive_carries']=progressive_carries

        # get the progressive passes
        progressive_passes = stats[23].text.strip()
        player_data['progressive_passes']=progressive_passes
        
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

