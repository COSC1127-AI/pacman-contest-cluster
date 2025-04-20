import streamlit as st  # https://docs.streamlit.io/streamlit-cloud/trust-and-security
import streamlit.components.v1 as components

import numpy as np
import pandas as pd
from pandas import json_normalize

import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import re
import os
import json
from datetime import datetime

import itables.interactive
from itables import show
from IPython.core.display import display, display_html, Javascript, HTML



# import all configuration vars
from config import SHOW_TEAMS_PROGRESS_CHECKBOX, DEPLOYED_URL, ORGANIZER, STATS_FOLDER

FORMAT_DATE_FILE = '.*(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}).*\.json'


def get_date_from_json(filename):
    """
    Extracts the date part of the json stat file
    :param filename:
    :return:
    """
    return re.match(FORMAT_DATE_FILE, filename).group(1)


def get_id_from_json(filename):
    """
    Extracts the date part of the json stat file
    :param filename:
    :return:
    """
    return re.match('stats_(.*).json', filename).group(1)


def normalize(x, min, max, min_new, max_new):
    """
    Normalize x in range (min, max) into new range (min_new, max_new)
    :param x:
    :param min:
    :param max:
    :param min_new:
    :param max_new:
    :return:
    """
    return (max_new - min_new) // (max - min) * (x - min) + min_new


# Streamlit encourages well-structured code, like starting execution in a main() function.
def main():
    max_width_layout()

    # Load Data
    json_files = sorted([f for f in os.listdir(STATS_FOLDER) if os.path.isfile(
        os.path.join(STATS_FOLDER, f))], reverse=True)

    df_all_games, df_all_stats = load_data(json_files)

    # Side bar
    json_selectbox = st.sidebar.selectbox(
        "Select Tournament",
        options=json_files,
        index=0,
        #format_func=lambda x: datetime.strptime(x, 'stats_%Y-%m-%d-%H-%M.json')
        format_func=lambda x: get_id_from_json(x)
    )

    table_checkbox = st.sidebar.checkbox('Show Table', value=True)

    if SHOW_TEAMS_PROGRESS_CHECKBOX:
        team_progress_checkbox = st.sidebar.checkbox(
            'Show Teams Progress Chart', value=True)
    games_checkbox = st.sidebar.checkbox('Show Games', value=True)
    games_pie_checkbox = st.sidebar.checkbox('Show Games Chart', value=True)

    df_games = df_all_games[json_selectbox]
    df_stats = df_all_stats[json_selectbox]
    timestamp_id = get_id_from_json(json_selectbox)

    st.image("pacman-banner-825x165.jpg")

    # Title Bar
    date_time_obj = get_date_from_json(json_selectbox)
    st.title(f'Pacman {ORGANIZER} Dashboard')
    st.header(f'Date: {date_time_obj}')
    

    # Show ladder table
    if table_checkbox:
        st.dataframe(df_stats.style.apply(lambda x: ['background: lightyellow' if (
            'staff_team' in x.name) else '' for i in x], axis=1), width=1500, height=1500)

    # Show Game Results
    st.markdown('# Games')

    # Extract set of teams
    team_names = np.unique(df_games[['Team1', 'Team2']].values)
    team_names_set = set(list(team_names))
    team_names_staff = set([x for x in team_names_set if x.startswith("staff_team")])
    team_names_students = team_names_set.difference(team_names_staff)

    # Select Team Results
    team_filter = st.selectbox('Filter by your team', options=[
                               "N/A"] + list(team_names_students), index=0)

    if team_filter != "N/A":
        #comparison = comparison.loc[(comparison['Team1'] == team_filter) | (comparison['Team2'] == team_filter) ]
        replays_link = f'## [Download Replays_{team_filter}.tar.gz]({DEPLOYED_URL}/replays-archive/replays_{timestamp_id}/replays_{team_filter}.tar.gz)'
        logs_link = f'## [Download Logs_{team_filter}.tar.gz]({DEPLOYED_URL}/logs-archive/logs_{timestamp_id}/logs_{team_filter}.tar.gz)'
        select_teams = [team_filter]

    else:
        replays_link = f'## [Download All Replays.tar.gz]({DEPLOYED_URL}/replays-archive/replays_{timestamp_id}.tar.gz)'
        logs_link = f'## [Download All Logs.tar.gz]({DEPLOYED_URL}/logs-archive/logs_{timestamp_id}.tar.gz)'
        select_teams = []

    st.markdown(replays_link)
    st.markdown(logs_link)

    if games_checkbox or games_pie_checkbox or team_progress_checkbox:
        select_teams_radio = st.radio(
            "Select Preselection of Opponents: ", ('All Teams', 'Staff Teams', 'None'), index=2)

        if select_teams_radio == 'All Teams':
            select_teams = team_names
        elif select_teams_radio == 'Staff Teams':
            select_teams += team_names_staff
        elif select_teams_radio == 'None' and team_filter != "N/A":
            select_teams = [team_filter]
        elif select_teams_radio == 'None' and team_filter == "N/A":
            select_teams = []

        teams_to_compare = st.multiselect(
            'Picked Teams', options=team_names_set, default=select_teams)

        comparison = df_games[(df_games['Team1'].isin(teams_to_compare)) & (
            df_games['Team2'].isin(teams_to_compare))]
        comparison = comparison.reset_index(drop=True)

        st.write('Number of matches: ', len(comparison))

    # Progress Chart
    if SHOW_TEAMS_PROGRESS_CHECKBOX:
        progress_chart(df_all_stats, teams_to_compare)

    # Plot Pie Chart
    if games_pie_checkbox:
        pie_chart_games(comparison, teams_to_compare)

    if games_checkbox:
        st.markdown('## Games Table')
        html_objects = show(comparison)
        components.html(html_objects, height=3800)


def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}">Download csv file</a>'

# Progress Chart


def progress_chart(df_all_stats, teams_to_compare):
    st.markdown(
        '# Position Progress (normalized 1-100) Since Start of Feedback Contests')
    fig6 = go.Figure()
    fig6['layout']['yaxis']['autorange'] = "reversed"
    fig6['layout']['width'] = 1200
    fig6['layout']['height'] = 600

    for tname in teams_to_compare:
        t_pos = []
        t_dates = []
        for competition in df_all_stats.keys():
            no_teams = len(df_all_stats[competition])
            if tname in df_all_stats[competition].index:
                # Records the % of position between 0 (top top) and 100 (very low)
                # t_pos += [(df_all_stats[competition].Position[tname] / no_teams) * 100]
                normalized_rank = normalize(
                    df_all_stats[competition].Position[tname], 1, no_teams, 1, 100)
                t_pos += [normalized_rank]

                # t_dates += [datetime.strptime(competition, 'stats_%Y-%m-%d-%H-%M.json')]
                t_dates += [datetime.strptime(
                    get_date_from_json(competition), '%Y-%m-%d-%H-%M')]

        fig6.add_trace(go.Scatter(x=t_dates, y=t_pos, name=tname))

    fig6.update_layout(
        xaxis=go.layout.XAxis(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )
    st.plotly_chart(fig6)

# Pie Chart


def pie_chart_games(comparison, teams_to_compare):
    games_t = {}
    wins_t = {}
    draws_t = {}
    total_draws = 0

    comparison_labels = []
    comparison_values = []

    for t in teams_to_compare:
        games_t[t] = comparison.loc[(comparison['Team1'] == t) | (
            comparison['Team2'] == t)]
        wins_t[t] = comparison[comparison['Winner'] == t]
        draws_t[t] = games_t[t].loc[games_t[t]['Winner'].isnull()]

        total_draws += len(draws_t[t].index)

        comparison_labels += [f'{t} wins']
        comparison_values += [len(wins_t[t].index)]

    total_draws /= 2

    comparison_labels += ['Draws']
    comparison_values += [total_draws]

    fig5 = go.Figure(
        data=[go.Pie(labels=comparison_labels, values=comparison_values)])
    fig5['layout']['width'] = 800
    fig5['layout']['height'] = 800
    st.markdown('## Games Pie Chart')

    st.plotly_chart(fig5)

# Layout


def max_width_layout():
    max_width_str = f"max-width: 2000px;"
    max_height_str = f"max-height: 3000px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
        {max_height_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )

# Loading Data


@st.cache
def load_data(json_files):
    df_games = {}
    df_stats = {}
    for fname in json_files:
        stats_file = os.path.join(STATS_FOLDER, fname)
        with open(stats_file) as f:
            d = json.load(f)

        # Create Games Dataframe
        timestamp_id = d['timestamp_id']
        df_games[fname] = json_normalize(d, 'games')
        df_games[fname].columns = ['Team1', 'Team2',
                                   'Layout', 'Score', 'Winner', 'Time']

        
        # Build replay download link per row; not sure why I cannot use formatted strings!
        replay_link_text = lambda t1, t2, lay: f"<a target=\"_blank\" onclick=\"alert('Right click to save. Alternatively, Refresh the new page opened and the dowload will start.')\" href=\"{DEPLOYED_URL}/replays-archive/replays_{timestamp_id}/" + t1 + "_vs_" + t2 + "_" + lay + ".replay\"> Download Replay </a>"
        df_games[fname] = df_games[fname].assign(ReplayFile=replay_link_text(df_games[fname]['Team1'], df_games[fname]['Team2'], df_games[fname]['Layout']))

        
        # Build log download link per row; not sure why I cannot use formatted strings!
        log_link_text = lambda t1, t2, lay: f"<a target=\"_blank\" href=\"{DEPLOYED_URL}/logs-archive/logs_{timestamp_id}/" + t1 + "_vs_" + t2 + "_" + lay + ".log\"> Download Log </a>"
        df_games[fname] = df_games[fname].assign(LogFile=log_link_text(df_games[fname].Team1 , df_games[fname].Team2, df_games[fname].Layout))

        # Create loeaderboard dataframe
        df_stats[fname] = pd.DataFrame(columns=['Percentage', 'Points', 'Win', 'Tie', 'Lost', 'FAILED', 'Score'],
                                       data=d['team_stats'].values(),
                                       index=d['team_stats'].keys()).sort_values(by=['Percentage', 'Points', 'Win', 'Score'], ascending=False)

        # df_stats[fname]['Percentage'].apply(np.floor, inPlace=True)

        # Create Position in the Table
        df_stats[fname]['Position'] = list(
            range(1, len(df_stats[fname].index)+1))

        # Rearrange Columns
        df_stats[fname] = df_stats[fname][['Position', 'Percentage', 'Points', 'Win', 'Tie', 'Lost', 'FAILED', 'Score']]

        # Round percentage to no decimals
        df_stats[fname]['Percentage'] = df_stats[fname]['Percentage'].round(decimals=0)
        df_stats[fname]['Percentage'] = df_stats[fname]['Percentage'].astype(int)

    return df_games, df_stats


if __name__ == "__main__":
    main()
