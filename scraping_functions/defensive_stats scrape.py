from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

teamLinks = ['https://fbref.com/en/comps/9/defense/Premier-League-Stats']

# create empty dictionary with attributes
players_info = {'name': [],
                'season': [],
                'competition': [], 
                'nation': [],
                'position': [], 
                'team': [],
                'age': [], 
                'year_born': [],
                'full_games': [],
                'tackles': [],
                'tackles_won': [],
                'def3_tackles': [],
                'mid3_tackles': [], 
                'att3_tackles': [],
                'tackle_percentage': [],
                'challenges_lost': [],
                'blocks': [], 
                'shots_blocked': [],
                'passes_blocked': [],
                'interceptions': [],
                'clearances': [],
                'error_shot': [],  }

for link in teamLinks:
    options = Options()
    driver = webdriver.Chrome(options=options)
    driver.get(link)
    time.sleep(0.5)
    source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(source, 'lxml')

    players=soup.find('div', id='all_stats_defense').find('tbody').find_all('tr')

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

        # get the full matches played
        full_games = stats[6].text.strip()
        player_data['full_games']=full_games

        # get the tackles 
        tackles = stats[7].text.strip()
        player_data['tackles']=tackles

        # get the tackles won
        tackles_won = stats[8].text.strip()
        player_data['tackles_won']=tackles_won

        # get the tackles in defensive 3rd 
        def3_tackles = stats[9].text.strip()
        player_data['def3_tackles']=def3_tackles

        # get the tackles in mid 3rd
        mid3_tackles = stats[10].text.strip()
        player_data['mid3_tackles']=mid3_tackles

        # get the attacking 3rd tackles
        att3_tackles = stats[11].text.strip()
        player_data['att3_tackles']=att3_tackles

        # get the tackle percentage
        tackle_percentage = stats[14].text.strip()
        player_data['tackle_percentage']=tackle_percentage

        # get the challenges lost
        challenges_lost = stats[15].text.strip()
        player_data['challenges_lost']=challenges_lost

        # get the blocks
        blocks = stats[16].text.strip()
        player_data['blocks']=blocks

        # get the shots blocked
        shots_blocked = stats[17].text.strip()
        player_data['shots_blocked']=shots_blocked

        # get the passes blocked
        passes_blocked = stats[18].text.strip()
        player_data['passes_blocked']=passes_blocked

        # get the interceptions
        interceptions = stats[19].text.strip()
        player_data['interceptions']=interceptions

        # get the clearances
        clearances = stats[21].text.strip()
        player_data['clearances']=clearances

        # get the errors leading to shot
        error_shot = stats[22].text.strip()
        player_data['error_shot']=error_shot
        
        # put all the information in the dictionary
        for key in players_info:
            players_info[key].append(player_data.get(key, None))
        

import pandas as pd

# create the data frame to display the data in row/col
df=pd.DataFrame(players_info)

# pd.set_option('display.max_rows', None)
print(df)

# create a csv file
df.to_csv('Prem player_defensive_stats.csv', index=False)



