import streamlit as st

import pandas as pd

import numpy as np

import re

from fuzzywuzzy import fuzz
import unicodedata

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager

import re
import os
import time
import math

import matplotlib.pyplot as plt
from collections import Counter
import seaborn as sns

from scipy.stats import linregress

#Configuración
import warnings
warnings.filterwarnings('ignore')
warnings.simplefilter(action='ignore', category=FutureWarning)

pd.set_option('display.max_columns', None)  # Show all columns


st.set_page_config(layout='wide')

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Ensure GUI is off
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

parquet_file_path = 'Data/Statsbomb_Roles_Potential.parquet'
data = pd.read_parquet(parquet_file_path)
data = data[['Player ID', 'Player', 'Team', 'League', 'Age', 'Minutes played', 'Position', 'Season',
             'Pass Ability', 'Ball Progression', 'Carry Ability', 'Dribbling Ability', 'Create Chances Ability',
             'Decision making', 'Positional awareness', '1v1 Defensive', 'Finishing Ability', 'Interception Ability', 'Aerial Ability',
             'Protect the goal', 'Pressing Intelligence', 'Link Up Play', 'Pass Between Lines', 'Movement Awareness of space','1v1 Attacking',
             'Quick Transition', 'Short Build Up', 'Ball Winner', 'Defensive Awareness', 'Defensive Responsibilities', 'Cross Ability',
             'Counterpress Regains', 'Counterpress Envolvement',
             'Role', 'Score', 'Percentile', 'Percentile_League', 'Grade_MLS', 'Grade_League']]

def install_geckodriver():
    os.system('sbase install geckodriver')
    os.system('ln -s /home/appuser/venv/lib/python3.7/site-packages/seleniumbase/drivers/geckodriver /home/appuser/venv/bin/geckodriver')

_ = install_geckodriver()

# Configure Firefox options
firefox_options = FirefoxOptions()
firefox_options.add_argument("--headless")  # Ensure GUI is off

def scrape_player_info(player_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Xll; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chorme/47.0.2526.106 Safari/537.36"
    }
    
    # Set path to geckodriver as per your configuration
    webdriver_service = Service(GeckoDriverManager().install())  # Automatically download and setup GeckoDriver

    # Create a webdriver instance
    driver = webdriver.Firefox(service=webdriver_service, options=firefox_options)

    # Fetch the webpage
    driver.get(player_url)

    # Wait for JavaScript to load
    time.sleep(3)

    # Get page source
    page_source = driver.page_source

    # Parse the rendered HTML with BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    
    player_info = {}

    # Find all elements with the specific class and data-testid attribute
    value_elements = soup.find_all('span', class_='percentage-value svelte-qus13h', attrs={'data-testid': 'gauge-percentage'})

    # Extract the text content from the second element (index 1)
    percentage_Minutes_Played = value_elements[1].text if len(value_elements) > 1 else None

    # Save the extracted value into the dictionary
    player_info['Minutes Percentage'] = percentage_Minutes_Played

    player_info['Url'] = player_url

    player_info['Id'] = player_url.split("spieler/")[1]

    # Extracting Team Name and League Name
    club_info = soup.find('div', class_='data-header__club-info')
    if club_info:
        team_name_tag = club_info.find('span', class_='data-header__club')
        if team_name_tag and team_name_tag.find('a'):
            player_info['Team'] = team_name_tag.find('a').get_text(strip=True)
        
        league_name_tag = club_info.find('span', class_='data-header__league')
        if league_name_tag and league_name_tag.find('a'):
            player_info['League'] = league_name_tag.find('a').get_text(strip=True)

    # Basic player information
    info_labels = soup.find_all('li', class_='data-header__label')
    for label in info_labels:
        key = label.get_text(strip=True).replace(':', ' ').split(' ')[0]
        if key == 'Former':
             key = 'International'
        value = label.find('span', class_='data-header__content')
        if value:
            text = value.get_text(strip=True)
            if key.startswith('Date'):
                #print(key, ' - ', text)
                # Separate the birth date and age
                #match = re.match(r'([A-Za-z]{3} \s*\d{2}, \s*\d{4}) \((\d+)\)', text)
                match = text.split(' ')[-1].split('(')[1].split(')')[0]
                match_2 = text.split(' (')[0]
                print(match)
                if match:
                    player_info['Date of birth'] = match_2
                    player_info['Age'] = match
            else:
                player_info[key] = text
            
    # Market value and last update
    market_value_div = soup.find('div', class_='data-header__box--small')
    if market_value_div:
        market_value = market_value_div.find('a', class_='data-header__market-value-wrapper').get_text(strip=True)
        player_info['Current Market Value'] = market_value.split(' ')[0].split('L')[0]  # Assuming the first part is the value
        last_update = market_value_div.find('p', class_='data-header__last-update').get_text(strip=True)
        player_info['Last update'] = last_update.replace('Last update:', '').strip()
    
    # Contract details
    contract_details = soup.find_all('span', class_='info-table__content')
    for i, detail in enumerate(contract_details):
        text = detail.get_text(strip=True)
        if ('Name in home country:' in text) or ('Full name' in text):
            full_name = contract_details[i + 1].get_text(strip=True)
            if '-' in full_name:
                # Get the name on the right side of the '-'
                player_name = full_name.split('-')[-1].strip()
            else:
                player_name = full_name
            player_info['Player'] = player_name
        # Only check for player name in the title if it wasn't already populated
        elif 'Player' not in player_info:
            # Extracting Team Name and League Name
            player_name_title = soup.find('title')
            if player_name_title:
                player_name_title = player_name_title.get_text(strip=True).split('-')[0].strip()
                player_info['Player'] = player_name_title
                
        elif 'Contract expires:' in text:
            player_info['Contract expires'] = contract_details[i + 1].get_text(strip=True)
        elif 'Last contract extension:' in text:
            player_info['Last contract ext'] = contract_details[i + 1].get_text(strip=True)
        elif 'Contract option:' in text:
            player_info['Contract Option'] = contract_details[i + 1].get_text(strip=True)
        elif 'Foot:' in text:
            player_info['Foot'] = contract_details[i + 1].get_text(strip=True)

    
    # Agente (assuming the agent's name is directly within a span without specific class)
    agent = soup.find(text=re.compile('Player agent:'))
    if agent and agent.parent:
        agent_info = agent.parent.find_next_sibling('span')
        if agent_info:
            player_info['Player agent'] = agent_info.get_text(strip=True)
    else:
        player_info['Player agent'] = 'No Info'

    data_player = pd.DataFrame([player_info])

    # List of all expected columns
    expected_columns = ['Id', 'Player', 'Age', 'Minutes Percentage', 'Height', 'Foot', 'Position', 'Team', 'League', 'Current Market Value', 'Last update', 'Contract expires', 'Contract Option', 'Player agent', 'Url']
    
    # Ensure all expected columns are in the DataFrame, fill with 'Sem Info' if missing
    for column in expected_columns:
        if column not in data_player.columns:
            data_player[column] = '0'
    
    # Reorder DataFrame according to expected_columns, to keep consistency across different players
    data_player = data_player[expected_columns]

    return data_player



def standardize_transfermarkt_url(url):
    # Use regex to find the part of the URL to replace
    standardized_url = re.sub(r'(https://www\.transfermarkt)\.[a-z]{2,3}(\.[a-z]{2})?(/.+)', r'\1.com\3', url)
    return standardized_url



def get_Injury_Track(url):
    # Get Injury profile
    url_player = url.replace("profil", "verletzungen")
    pid = url_player.split("spieler/")[1]

    #Request
    headers = {
        "User-Agent": "Mozilla/5.0 (Xll; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chorme/47.0.2526.106 Safari/537.36"
    }

    response = requests.get(url_player, headers=headers)
    print(response)
    if response.status_code == 200: 
        soup = BeautifulSoup(response.content, 'html.parser')
        if soup.find("table", class_ = "items") != None:

            temp = pd.read_html(str(soup.find("table", class_ = "items")))[0]

            pager_div = soup.find("div", class_="pager")
            page_count = 0  # Initialize page_count
            if pager_div is not None:
                pages = pager_div.find_all("a", class_="tm-pagination__link")
                page_count = len(pages) - 2  # Subtracting the last two navigation links (next and last page)
                print("Injury Pages:", page_count)
            else:
                print("Injury Pages: 0")

            if page_count > 1:
                for page_num in np.arange(2, page_count + 1, 1):
                    url2 = url_player + "/ajax/yw1/page/" + str(page_num)
                    response = requests.get(url2, headers=headers)
                    soup2 = BeautifulSoup(response.content, "html.parser")
                    temp_table2 = pd.read_html(str(soup2.find("table", class_="items")))[0]
                    temp = pd.concat([temp, temp_table2], ignore_index=True)

            temp["TMId"] = pid

            # Extracting only the numbers and converting to integers
            temp['Days'] = temp['Days'].str.extract('(\d+)').astype(int)
            temp['Games missed'] = temp['Games missed'].replace('-', 0)
            temp['Games missed'] = temp['Games missed'].fillna(0)
            temp = temp.rename({'Games missed' : 'Games'}, axis=1)
        else:
            print('No Injury data available.')
            temp = pd.DataFrame(columns=['Season', 'Injury', 'from', 'until', 'Days', 'Games', 'TMId'])
    else:
        print('No Injury data available.')
        temp = pd.DataFrame(columns=['Season', 'Injury', 'from', 'until', 'Days', 'Games', 'TMId'])

    return temp



def merge_all_data(df_player, dfInjury):
    # Convert 'Days' and 'Games' columns to numeric
    dfInjury['Days'] = pd.to_numeric(dfInjury['Days'], errors='coerce')
    dfInjury['Games'] = pd.to_numeric(dfInjury['Games'], errors='coerce')

    # Group by Season and TMId, and aggregate the required columns
    dfInjury_grouped = dfInjury.groupby(['Season', 'TMId']).agg({
        'Days': 'sum',
        'Games': 'sum',
        'Injury': lambda x: list(x)
    }).reset_index()

    # Rename columns to avoid conflicts
    dfInjury_grouped.rename(columns={'Days': 'Total Days', 'Games': 'Total Games missed', 'Injury': 'Injuries'}, inplace=True)

    # Merge the dataframes
    transfermarkt_df = pd.merge(df_player, dfInjury_grouped, left_on='Id', right_on='TMId', how='left')

    # Reorder columns as specified
    columns_order = [
        'Id', 'Season', 'Player', 'Age', 'Minutes Played', 'Minutes Percentage', 'Height', 'Foot', 'Position', 
        'Current Market Value', 'Team', 'League', 'Injuries', 'Total Days', 
        'Total Games missed', 'Contract expires', 'Contract Option', 
        'Player agent', 'Url'
    ]
    transfermarkt_df = transfermarkt_df[columns_order]
    transfermarkt_df[['Season', 'Total Days', 'Total Games missed', 'Injuries']] = transfermarkt_df[['Season', 'Total Days', 'Total Games missed', 'Injuries']].fillna('No Data Available')
        
    return transfermarkt_df



def remove_accents(player_name):
    nfkd_form = unicodedata.normalize('NFKD', player_name)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])



# Streamlit app
# Center the title
st.markdown(
    """
    <style>
    .center-title {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<h1 class="center-title">MNUFC Web App</h1>', unsafe_allow_html=True)

# User input for URL
url = st.text_input('Enter the URL of the transfermarkt:')

# Button to run the scraper
if st.button('Get Data'):
    if url:
        # Call the function to scrape the website and get the DataFrame
        try:
            url = standardize_transfermarkt_url(url)

            dfPlayer = scrape_player_info(url)

            df_Injury = get_Injury_Track(url)

            transfermarkt_df = merge_all_data(dfPlayer, df_Injury)
                
            # Applying the function to both dataframes
            transfermarkt_df['Player'] = transfermarkt_df['Player'].apply(remove_accents)
            data['Player'] = data['Player'].apply(remove_accents)

            playerName = transfermarkt_df['Player'].unique()[0]
            player = data[(data['Player'].str.contains(playerName))].reset_index(drop=True)
            print(player)
    
            # Selecting the necessary columns from transfermarkt_df
            transfermarkt_selected = transfermarkt_df[['Player', 'Minutes Percentage', 'Foot', 'Height', 'Current Market Value', 'Injuries', 'Total Days', 'Total Games missed', 'Contract expires', 'Contract Option', 'Player agent']]

            try:
                # Merging the dataframes based on 'Player' column
                merged_df = pd.merge(player, transfermarkt_selected, on='Player', how='left')

                if merged_df.empty:
                    raise IndexError("index 0 is out of bounds for axis 0 with size 0")

                # Reorder columns as specified
                columns_order = [
                    'Player ID', 'Season', 'Player', 'Age', 'Minutes Played', 'Minutes Percentage', 'Height', 'Foot', 'Position', 
                    'Current Market Value', 'Team', 'League', 'Contract expires', 'Contract Option', 
                    'Player agent', 'Percentile', 'Grade_MLS', 'Percentile_League', 'Grade_League'
                ]

                merged_df = merged_df[columns_order]

                Percentile = int(merged_df['Percentile'].mean())
                mls_Grade = str(merged_df['Grade_MLS'].unique()[0])
                minutes_Percentage = int(merged_df['Minutes Percentage'].unique()[0])

                if minutes_Percentage == 0:
                    minutes_Percentage = str(merged_df['Minutes Played'].unique()[0])

                st.dataframe(merged_df, use_container_width=True)

                col1, col2, col3 = st.columns(3)

                col1.metric("Percentile", Percentile, "")

                col2.metric("Minutes Percentage", minutes_Percentage, "")

                col3.metric("Grade MLS Context", mls_Grade, "")

                st.download_button(
                    label="Download data as CSV",
                    data=merged_df.to_csv(index=False).encode('utf-8'),
                    file_name='player_data_statsbomb_transfermarkt.csv',
                    mime='text/csv',
                )

                if df_Injury.empty:
                    pass
                    # Center the title
                    st.markdown(
                        """
                        <style>
                        .center-title {
                            text-align: center;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown('<h1 class="center-title">No injury history</h1>', unsafe_allow_html=True)
                else:
                    # Center the title
                    st.markdown(
                        """
                        <style>
                        .center-title {
                            text-align: center;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown('<h1 class="center-title">Injury History</h1>', unsafe_allow_html=True)

                    # Create two empty columns and one column for the DataFrame
                    col1, col2, col3 = st.columns([1.7, 2, 1])

                    # Center the DataFrame in the middle column
                    with col2:
                        st.dataframe(df_Injury[['Season', 'Days', 'Games', 'Injury']])

                    # Group by season and calculate the total days and games missed per season
                    total_injury = df_Injury.groupby('Season').agg({'Days': 'sum', 'Games': 'sum'}).reset_index()

                    # Calculate the average total days and games missed across all seasons
                    average_days = int(total_injury['Days'].mean() if not total_injury['Days'].empty else 0)
                    average_games = int(total_injury['Games'].mean() if not total_injury['Games'].empty else 0)

                    # Center the metrics using columns
                    col1, col2, col3 = st.columns([1, 2, 1])

                    with col2:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Average Days missed", average_days)
                        with col2:
                            st.metric("Average Games missed", average_games)
                    # Centered section
                    with st.expander("More in-depth injury analyses"):
                        # Center the title
                        st.markdown(
                            """
                            <style>
                            .center-title {
                                text-align: center;
                            }
                            </style>
                            """,
                            unsafe_allow_html=True
                        )

                        
                        #st.markdown('<h1 class="center-title">More in-depth injury analyses</h1>', unsafe_allow_html=True)

                        # Calculate yearly statistics
                        transfermarkt_df['Number of Injuries'] = transfermarkt_df['Injuries'].apply(len)

                        # Identify all unique injury types
                        all_injuries = [injury for sublist in transfermarkt_df['Injuries'] for injury in sublist]
                        injury_counts = Counter(all_injuries)

                        # Select injuries that appear in more than one season
                        frequent_injuries = [injury for injury, count in injury_counts.items() if count > 1]

                        # Add columns for each frequent injury type
                        for injury_type in frequent_injuries:
                            transfermarkt_df[injury_type] = transfermarkt_df['Injuries'].apply(lambda x: x.count(injury_type))

                        # Add a column for ligament tear severity
                        transfermarkt_df['Ligament Tear'] = transfermarkt_df['Injuries'].apply(lambda x: 1 if 'ligament tear' in ' '.join(x).lower() else 0)

                        # Function to check trend
                        def check_trend(data, column):
                            x = list(range(len(data)))
                            y = data[column].values
                            slope, intercept, r_value, p_value, std_err = linregress(x, y)
                            return slope, p_value

                        # Check trends for Total Days, Total Games missed, Number of Injuries, frequent injury types, and ligament tears
                        columns_to_check = ['Total Days', 'Total Games missed', 'Number of Injuries']
                        trends = {col: check_trend(transfermarkt_df, col) for col in columns_to_check}

                        # Determine the grid size for subplots
                        n_columns = 3
                        n_rows = math.ceil(len(columns_to_check) / n_columns)

                        # Plotting the data to visually inspect trends
                        fig, axes = plt.subplots(n_rows, n_columns, figsize=(n_columns * 5, n_rows * 5))
                        axes = axes.flatten()

                        for i, column in enumerate(columns_to_check):
                            axes[i].plot(transfermarkt_df['Season'], transfermarkt_df[column], marker='o')
                            axes[i].set_title(f'{column} Over Seasons')
                            axes[i].set_xlabel('Season')
                            axes[i].set_ylabel(column)
                            axes[i].tick_params(axis='x', rotation=45)

                        plt.tight_layout()
                        st.pyplot(fig)

                        # Cumulative analysis for frequent injuries
                        fig2, ax2 = plt.subplots(figsize=(15, 10))
                        cumulative_counts = transfermarkt_df[frequent_injuries + ['Ligament Tear']].cumsum()

                        for injury_type in frequent_injuries + ['Ligament Tear']:
                            ax2.plot(transfermarkt_df['Season'], cumulative_counts[injury_type], marker='o', label=injury_type)

                        ax2.set_title('Cumulative Count of Frequent and Severe Injuries Over Seasons')
                        ax2.set_xlabel('Season')
                        ax2.set_ylabel('Cumulative Count')
                        ax2.tick_params(axis='x', rotation=45)
                        ax2.legend()

                        st.pyplot(fig2)

                        # Analyze trends
                        trend_analysis = {}
                        for col, (slope, p_value) in trends.items():
                            if p_value < 0.05:
                                trend_analysis[col] = f"Significant trend detected with slope {slope:.2f} and p-value {p_value:.2f}"
                            else:
                                trend_analysis[col] = "No significant trend detected"

            except IndexError:
                if not player.empty:
                    statsbomb_Name = player['Player'].unique()[0]
                    transfermarkt_Name = transfermarkt_selected['Player'].unique()[0]
                    if statsbomb_Name != transfermarkt_Name:
                        st.warning("StatsBomb data available but names don't match")
                    else:
                        st.warning("No StatsBomb data available for that player, please insert another one.")
                else:
                    st.warning("No StatsBomb data available for that player, please insert another one.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.error("Please enter a URL to scrape.")