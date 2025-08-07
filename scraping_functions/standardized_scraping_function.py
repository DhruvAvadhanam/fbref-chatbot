from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import pandas as pd

# create a configuration dictionary to determine the stat type
STAT_CONFIG = {
    'standard': {
        'url_template': 'https://fbref.com/en/comps/9/{season}/stats/{season}-{competition}-Stats',
        'div_id': 'div_stats_standard',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'matches', 'starts', 'minutes', 'full_games',
            'goals', 'assists', 'G+A', 'non-PK_goals', 'PK_goals', 'PK_att', 'yellow_cards', 'red_cards',
            'xG', 'xG_nonpenalty', 'xGA', 'xGnp+xGA', 'progressive_carries', 'progressive_passes'
        ]
    },
    'keeper': {
        'url_template': 'https://fbref.com/en/comps/9/{season}/keepers/{season}-{competition}-Stats',
        'div_id': 'all_stats_keeper',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'matches', 'starts', 'minutes', 'full_games',
            'goals_against', 'goals_against_per90', 'shots_ontarget_against', 'saves', 'save_percentage',
            'wins', 'draws', 'losses', 'clean_sheets', 'clean_sheet_percentage', 'PK_att_against',
            'PK_conceded', 'PK_saved', None, 'PK_save_percentage'
        ]
    },
    'defensive': {
        'url_template': 'https://fbref.com/en/comps/9/{season}/defense/{season}-{competition}-Stats',
        'div_id': 'all_stats_defense',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'full_games', 'tackles', 'tackles_won',
            'def3_tackles', 'mid3_tackles', 'att3_tackles', None, None, 'tackle_percentage',
            'challenges_lost', 'blocks', 'shots_blocked', 'passes_blocked', 'interceptions',
            None, 'clearances', 'error_shot'
        ]
    }
}

def scrape_fbref(stat_type='standard', season='2024/2025', competition='Premier League'):
    config = STAT_CONFIG[stat_type]
    url = config['url_template'].format(season=season, competition=competition)
    div_id = config['div_id']
    columns = config['columns']

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    driver.quit()

    # create a list of each column in the dictionary
    players_info = {col: [] for col in columns if col}
    players_info.update({'season': [], 'competition': []})

    players = soup.find('div', id=div_id).find('tbody').find_all('tr')

    for player in players:
        if 'class' in player.attrs and 'thead' in player['class']:
            continue

        tds = player.find_all('td')
        row = {}

        for i, col in enumerate(columns):
            if not col:
                continue

            if i < len(tds):
                if col == 'nation':
                    nation_text = tds[i].get_text(separator=" ").strip()
                    row[col] = nation_text.split()[-1] if nation_text else None
                else:
                    a_tag = tds[i].find('a')
                    row[col] = a_tag.text.strip() if a_tag else tds[i].text.strip()
            else:
                row[col] = None

        # Add metadata
        row['season'] = season
        row['competition'] = competition

        for col in players_info:
            players_info[col].append(row.get(col, None))

    df = pd.DataFrame(players_info)
    return df.to_string(index=False)


def scrape_fbref_df(stat_type='standard', season='2024/2025', competition='Premier League'):
    config = STAT_CONFIG[stat_type]
    url = config['url_template'].format(season=season, competition=competition)
    div_id = config['div_id']
    columns = config['columns']

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    print(url)
    driver.get(url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    driver.quit()

    # create a list of each column in the dictionary
    players_info = {col: [] for col in columns if col}
    players_info.update({'season': [], 'competition': []})

    players = soup.find('div', id=div_id).find('tbody').find_all('tr')

    for player in players:
        if 'class' in player.attrs and 'thead' in player['class']:
            continue

        tds = player.find_all('td')
        row = {}

        for i, col in enumerate(columns):
            if not col:
                continue

            if i < len(tds):
                if col == 'nation':
                    nation_text = tds[i].get_text(separator=" ").strip()
                    row[col] = nation_text.split()[-1] if nation_text else None
                else:
                    a_tag = tds[i].find('a')
                    row[col] = a_tag.text.strip() if a_tag else tds[i].text.strip()
            else:
                row[col] = None

        # Add metadata
        row['season'] = season
        row['competition'] = competition

        for col in players_info:
            players_info[col].append(row.get(col, None))

    df = pd.DataFrame(players_info)
    return df

# df_keeper = scrape_fbref('keeper', '2024/2025', 'Premier League')




