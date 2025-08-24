from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import cloudscraper

# Mapping of league names to their FBref competition ID
LEAGUE_ID_MAP = {
    "Premier-League": "9",
    "La-Liga": "12",
    "Serie-A": "11",
    "Bundesliga": "20",
    "Ligue-1": "13"
}

# create a configuration dictionary to determine the stat type
STAT_CONFIG = {
    'standard': {
        'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/stats/{season}-{competition}-Stats',
        'div_id': 'div_stats_standard',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'matches', 'starts', 'minutes', 'full_games',
            'goals', 'assists', 'G+A', 'non-PK_goals', 'PK_goals', 'PK_att', 'yellow_cards', 'red_cards',
            'expected_goals(xG)', 'xG_nonpenalty', 'xGA', 'xGnp+xGA', 'progressive_carries', 'progressive_passes'
        ]
    },
    'keeper': {
        'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/keepers/{season}-{competition}-Stats',
        'div_id': 'all_stats_keeper',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'matches', 'starts', 'minutes', 'full_games',
            'goals_against', 'goals_against_per90', 'shots_ontarget_against', 'saves', 'save_percentage',
            'wins', 'draws', 'losses', 'clean_sheets', 'clean_sheet_percentage', 'PK_att_against',
            'PK_conceded', 'PK_saved', None, 'PK_save_percentage'
        ]
    },
    'defensive': {
        'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/defense/{season}-{competition}-Stats',
        'div_id': 'all_stats_defense',
        'columns': [
            'name', 'nation', 'position', 'team', 'age', 'year_born', 'full_games', 'tackles', 'tackles_won',
            'def3_tackles', 'mid3_tackles', 'att3_tackles', None, None, 'tackle_percentage',
            'challenges_lost', 'blocks', 'shots_blocked', 'passes_blocked', 'interceptions',
            None, 'clearances', 'error_shot'
        ]
    },
    'shooting': {
    'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/shooting/{season}-{competition}-Stats',
    'div_id': 'all_stats_shooting',
    'columns': [
        'name', 'nation', 'position', 'team', 'age', 'year_born', 'full_games', 'goals', 'shots',
        'shots_on_target', 'shots_on_target_percentage', 'shots_per_90', 'goals_per_shot', 'goals_per_shot_on_target',
        'average_shot_distance', 'shots_from_free_kicks', 'PK_goals', 'PK_att', 'xG', 'xG_nonpenalty',
        'xG_nonpenalty_per_shot', 'goals-xG', 'nonpenalty_goals-xG_nonpenalty'
    ]
    },
    'passing': {
    'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/passing/{season}-{competition}-Stats',
    'div_id': 'all_stats_passing',
    'columns': [
        'name', 'nation', 'position', 'team', 'age', 'year_born', 'full_games', 'completed_passes', 'pass_attempts',
        'pass_completion_percentage', 'passing_distance', 'progressive_passes_distance', 'short_pass_completed', 
        'short_pass_attempts','short_pass_completion_percentage', 'medium_pass_completed', 
        'medium_pass_attempts', 'medium_pass_completion_percentage', 'long_pass_completed', 'long_pass_attempts',
        'long_pass_completion_percentage', 'assists', None, 'expected_assists(xA)', None, 'key_passes', 'passes_into_final_third',
        'passes_into_penalty_area', 'crosses_into_penalty_area', 'progressive_passes'
    ]
    },
    'possession': {
    'url_template': 'https://fbref.com/en/comps/{competition_id}/{season}/possession/{season}-{competition}-Stats',
    'div_id': 'all_stats_possession',
    'columns': [
        'name', 'nation', 'position', 'team', 'age', 'year_born', 'full_games', 'touches', 'touches_defensive_pen_area',
        'touches_defensive_third', 'touches_mid_third', 'touches_attacking_third', 'touches_attacking_pen_area', 
        'live_ball_touches','take_on_attempts', 'successful_take_on', 'take_on_percentage', 'tackled_during_take_on', 
        None, 'ball_carries', 'total_carry_distance', 'progressive_carry_distance', 'progressive_carries', 'carries_into_final_third',
        'carries_into_penalty_area', 'miscontrols', 'dispossessed', 'passes_recieved', 'progressive_passes_recieved'
    ]
    }
}

def _read_url_content(url: str):
        scraper = cloudscraper.create_scraper()  # creates a scraper instance
        response = scraper.get(url)
        html_content = response.text
        return html_content

def scrape_fbref(stat_type='standard', season='2024-2025', competition='Premier-League'):
    config = STAT_CONFIG[stat_type]
    competition_id = LEAGUE_ID_MAP.get(competition)
    url = config['url_template'].format(season=season, competition=competition, competition_id=competition_id)
    div_id = config['div_id']
    columns = config['columns']

    options = Options()
    options.add_argument("--headless")

    # driver = webdriver.Chrome(options=options)
    # driver.get(url)
    time.sleep(3)
    html_content = _read_url_content(url)
    soup = BeautifulSoup(html_content, 'lxml')
    # soup = BeautifulSoup(driver.page_source, 'lxml')
    # driver.quit()

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


def scrape_fbref_df(stat_type='standard', season='2024-2025', competition='Premier-League'):
    config = STAT_CONFIG[stat_type]
    competition_id = LEAGUE_ID_MAP.get(competition)
    url = config['url_template'].format(season=season, competition=competition, competition_id=competition_id)
    div_id = config['div_id']
    columns = config['columns']

    options = Options()
    options.add_argument("--headless")
    # driver = webdriver.Chrome(options=options)
    # driver.get(url)
    time.sleep(3)
    html_content = _read_url_content(url)
    soup = BeautifulSoup(html_content, 'lxml')
    # soup = BeautifulSoup(driver.page_source, 'lxml')
    # driver.quit()

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


df_bundesliga_defense = scrape_fbref_df('defensive', '2024-2025', 'Bundesliga')
print(df_bundesliga_defense)



