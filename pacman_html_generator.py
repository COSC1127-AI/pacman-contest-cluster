#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Generates the HTML output given logs of the past tournament runs.
"""
__author__      = "Sebastian Sardina, Marco Tamassia, Nir Lipovetzky, and Andrew Chester"
__copyright__   = "Copyright 2017-2021"
__license__     = "GPLv3"

#  ----------------------------------------------------------------------------------------------------------------------
# Import standard stuff

import os
import sys
import argparse
import json
import shutil
import zipfile
import logging
import re
import datetime
from pytz import timezone
from config import *


# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG, datefmt='%a, %d %b %Y %H:%M:%S')
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                    datefmt='%a, %d %b %Y %H:%M:%S')

DIR_SCRIPT = sys.path[0]
FILE_FONTS = os.path.join(DIR_SCRIPT, "fonts.zip")
FILE_CSS = os.path.join(DIR_SCRIPT, "style.css")

# ----------------------------------------------------------------------------------------------------------------------
# Load settings either from config.json or from the command line

def load_settings():
    DEFAULT_CONFIG_FILE = 'config.json'

    parser = argparse.ArgumentParser(
        description='This script generates the HTML structure given the logs of all the runs of this tournament.'
    )
    parser.add_argument(
        dest='organizer', type=str,
        help='name of the organizer of the contest'
    )
    parser.add_argument(
        dest='www_dir', type=str,
        help='output directory containing sats, replays, and log files'
    )
    args = parser.parse_args()


    # If no arguments are given, stop
    if len(sys.argv) == 1:
        print('No arguments given. Use -h fo help')
        sys.exit(0)

    # First get the options from the configuration file if available
    settings = {}
    # if not args.config_file is None:
    #     if os.path.exists(args.config_file):
    #         with open(args.config_file, 'r') as f:
    #             settings = json.load(f)
    #             logging.debug('Configuration file loaded')
    #     else:
    #         logging.error('Configuration file selected not available')
    #         settings = {}

    # if given, set the parameters as per command line options (may override config file)
    if args.organizer:
        settings['organizer'] = args.organizer
    if args.www_dir:
        settings['www_dir'] = args.www_dir

    # Check mandatory parameters are there, otherwise quit
    missing_parameters = {'organizer', 'www_dir'} - set(settings.keys())
    if missing_parameters:
        logging.error('Missing parameters: %s. Aborting.' % list(sorted(missing_parameters)))
        parser.print_help()
        sys.exit(1)

    settings['stats_archive_dir'] = os.path.join(settings['www_dir'], STATS_ARCHIVE_DIR)
    settings['replays_archive_dir'] = os.path.join(settings['www_dir'], REPLAYS_ARCHIVE_DIR)
    settings['logs_archive_dir'] = os.path.join(settings['www_dir'], LOGS_ARCHIVE_DIR)

    logging.info('Script will run with this configuration: %s' % settings)

    return settings


# ----------------------------------------------------------------------------------------------------------------------

class HtmlGenerator:
    def __init__(self, www_dir, organizer, score_thresholds=None):
        """
        Initializes this generator.

        :param www_dir: the output path
        :param organizer: the name of the organizer of the tournament (e.g., XX University)
        """

        # path that contains files that make-up a html navigable web folder
        self.www_dir = www_dir

        # just used in html as a readable string
        self.organizer = organizer
        self.score_thresholds = score_thresholds


    def _close(self):
        pass

    def clean_up(self):
        """
        Empties and removes the output directory
        """
        shutil.rmtree(self.www_dir)

    def add_run(self, run_id, stats_dir, replays_dir, logs_dir):
        """
        (Re)Generates the HTML for the given run and updates the HTML index.
        :return:
        """
        self._save_run_html(run_id, stats_dir, replays_dir, logs_dir)
        self._generate_main_html()

    def _save_run_html(self, run_id, stats_file, replays_file, logs_file):
        """
        Generates the HTML of a contest run and saves it in www/results_<run_id>/results.html.

        The URLs passed should be either:
         - HTTP URLs, in which case the stats file is downloaded to generate the HTML
         - local relative paths, which are assumed to start from self.www_dir

        No checks are done, so mind your parameters.
        """
        # The URLs may be in byte format - convert them to strings if needed
        try:
            stats_file = stats_file.decode()
        except AttributeError:
            pass
        try:
            replays_file= replays_file.decode()
        except AttributeError:
            pass
        try:
            logs_file= logs_file.decode()
        except AttributeError:
            pass

        # Get the information in the stats file
        if stats_file.startswith('http'):  # http url
            import urllib.request as request
            content = request(stats_file).read()
            data = json.loads(content)

        else:  # relative path
            # prepend www/ so the file can be opened by this script, which is somewhere else
            stats_file_path = os.path.join(self.www_dir, stats_file)

            with open(stats_file_path, 'r') as f:
                data = json.load(f)

        games = data['games']
        max_steps = data['max_steps']
        team_stats = data['team_stats']
        random_layouts = data['random_layouts']
        fixed_layouts = data['fixed_layouts']
        if 'organizer' in data.keys():
            organizer = data['organizer']
        else:
            organizer = None
        if 'timestamp_id' in data.keys():
            date_run = data['timestamp_id']
        else:
            date_run = run_id

        #  check if json data file contains the links to the replays and logs, if so, used them!
        if 'url_replays' in data:
            replays_file = data['url_replays']
        if 'url_logs' in data:
            logs_file = data['url_logs']

        if not os.path.exists(self.www_dir):
            os.makedirs(self.www_dir)
        contest_zip_file = zipfile.ZipFile(FILE_FONTS)
        contest_zip_file.extractall(self.www_dir)
        shutil.copy(FILE_CSS, self.www_dir)

        run_html = self._generate_output(run_id, date_run, organizer, games, team_stats, random_layouts, fixed_layouts,
                                         max_steps,
                                         stats_file, replays_file, logs_file)

        html_full_path = os.path.join(self.www_dir, f'results_{run_id}.html')
        with open(html_full_path, "w") as f:
            print(run_html, file=f)

    def _generate_main_html(self):
        """
        Generates the index HTML, containing links to the HTML files of all the runs.
        The file is saved in www/results.html.
        """
        # regenerate main html
        main_html = """<html><head><title>Results for PACMAN Capture the Flag the tournament</title>\n"""
        main_html += """<link rel="stylesheet" type="text/css" href="style.css"/></head>\n"""
        main_html += """<body><h1>Results Pacman Capture the Flag by Date</h1>\n"""
        main_html += """<body><h2>Organizer: %s </h1>\n\n""" % self.organizer
        for d in sorted(os.listdir(self.www_dir)):
            if d.endswith('fonts'):
                continue
            if not d.startswith('results'):
                continue
            main_html += f"""<a href="{d}"> {d[:-5]}  </a> <br/>\n"""
        main_html += "\n\n<br/></body></html>"
        with open(os.path.join(self.www_dir, 'index.html'), "w") as f:
            print(main_html, file=f)

    def _generate_output(self, run_id, date_run, organizer, games, team_stats, random_layouts, fixed_layouts, max_steps,
                         stats_dir, replays_dir, logs_dir):
        """
        Generates the HTML of the report of the run.
        """

        if organizer is None:
            organizer = self.organizer

        output = """<html><head><title>Results for the tournament round</title>\n"""
        output += """<link rel="stylesheet" type="text/css" href="style.css"/></head>\n"""
        output += """<body><h1>PACMAN Capture the Flag Tournament</h1>\n"""
        output += """<body><h2>Tournament Organizer: %s </h1>\n""" % organizer
        if not run_id == date_run:
            output += """<body><h2>Name of Tournament: %s </h1>\n""" % run_id
        output += """<body><h2>Date of Tournament: %s \n</h1>""" % date_run

        output += """<h2>Configuration: %d teams in %d (%d fixed + %d random) layouts for %d steps</h2>\n""" \
                  % (len(team_stats), len(fixed_layouts) + len(random_layouts), len(fixed_layouts), len(random_layouts),
                     max_steps)

        # output += """<h2>Configuration:</h2><ul>"""
        # output += """<li>No. of teams: %d</li>""" % len(team_stats)
        # output += """<li>No. of layouts: %d (%d fixed + %d random)</li>""" % \
        #           (len(fixed_layouts) + len(random_layouts), len(fixed_layouts), len(random_layouts))
        # output += """<li>No. of steps: %d</li>""" % self.max_steps
        # output += """</ul><br/>"""



        # This actually enumerates the list of layouts, not needed... :-)
        # if fixed_layouts:
        #     s = '</li><li>'.join(fixed_layouts)
        #     output += """<h3>Fixed layouts</h2><ul><li>%s</li></ul><br/>""" % s
        # if random_layouts:
        #     s = '</li><li>'.join(random_layouts)
        #     output += """<h3>Random layouts</h2><ul><li>%s</li></ul><br/>""" % s

        output += """<br/><br/><table border="1">"""
        if len(games) == 0:
            output += "No match was run."
        else:
            # First, print a table with the final standing
            output += """<tr>"""
            output += """<th>Position</th>"""
            output += """<th>Team</th>"""
            output += """<th>Points %</th>"""
            output += """<th>Points</th>"""
            output += """<th>Win</th>"""
            output += """<th>Tie</th>"""
            output += """<th>Lost</th>"""
            output += """<th>TOTAL</th>"""
            output += """<th>FAILED</th>"""
            output += """<th>Score Balance</th>"""
            output += """</tr>\n"""

            # If score thresholds exist for table, sort in reverse order and add -1 as terminal boundary
            if self.score_thresholds is None:
                score_thresholds = [-1]
            else:
                score_thresholds = sorted(self.score_thresholds,reverse=True) + [-1]

            next_threshold_index = 0

            # Sort teams by points_pct v[1][0] first, then no. of wins, then score points.
            # example list(team_stats.items() = [('TYGA_THUG', [6, 2, 0, 0, 0, 2]), ('RationalAgents_', [0, 0, 0, 2, 2, -2])]
            sorted_team_stats = sorted(list(team_stats.items()), key=lambda v: (v[1][0], v[1][2], v[1][6]), reverse=True)
            position = 0
            for key, (points_pct, points, wins, draws, losses, errors, sum_score) in sorted_team_stats:
                while score_thresholds[next_threshold_index] > points_pct:
                    output +="""<tr bgcolor="#D35400"><td colspan="10" style="text-align:center">%d%% </td></tr>\n""" % score_thresholds[next_threshold_index]
                    next_threshold_index+=1
                position += 1
                output += """<tr>"""
                output += """<td>%d</td>""" % position
                output += """<td>%s</td>""" % key
                output += """<td>%d%%</td>""" % points_pct
                output += """<td>%d</td>""" % points
                output += """<td>%d</td>""" % wins
                output += """<td >%d</td>""" % draws
                output += """<td>%d</td>""" % losses
                output += """<td>%d</td>""" % (wins + draws + losses)
                output += """<td >%d</td>""" % errors
                output += """<td >%d</td>""" % sum_score
                output += """</tr>\n"""
            output += "</table>"


            # Second, print each game result
            output += "\n\n<br/><br/><h2>Games</h2>\n"

            times_taken = [time_game for (_, _, _, _, _, time_game) in games]
            output += """<h3>No. of games: %d / Avg. game length: %s / Max game length: %s</h3>\n""" \
                      % (len(games), str(datetime.timedelta(seconds=round(sum(times_taken) / len(times_taken),0))),
                         str(datetime.timedelta(seconds=max(times_taken))))

            if replays_dir:
                output += """<a href="%s">DOWNLOAD REPLAYS</a><br/>\n""" % replays_dir
            if logs_dir:
                output += """<a href="%s">DOWNLOAD LOGS</a><br/>\n""" % logs_dir
            if stats_dir:
                output += """<a href="%s">DOWNLOAD STATS</a><br/>\n\n""" % stats_dir
            output += """<table border="1">"""
            output += """<tr>"""
            output += """<th>Team 1</th>"""
            output += """<th>Team 2</th>"""
            output += """<th>Layout</th>"""
            output += """<th>Time</th>"""
            output += """<th>Score</th>"""
            output += """<th>Winner</th>"""
            output += """</tr>\n"""
            for (n1, n2, layout, score, winner, time_taken) in games:
                output += """<tr>"""

                # Team 1
                output += """<td align="center">"""
                if winner == n1:
                    output += "<b>%s</b>" % n1
                else:
                    output += "%s" % n1
                output += """</td>"""

                # Team 2
                output += """<td align="center">"""
                if winner == n2:
                    output += "<b>%s</b>" % n2
                else:
                    output += "%s" % n2
                output += """</td>"""

                # Layout
                output += """<td>%s</td>""" % layout

                # Time taken in the game
                output += """<td>%s</td>""" % str(datetime.timedelta(seconds=time_taken))

                # Score and Winner
                if score == ERROR_SCORE:
                    if winner == n1:
                        output += """<td >--</td>"""
                        output += """<td><b>ONLY FAILED: %s</b></td>""" % n2
                    elif winner == n2:
                        output += """<td >--</td>"""
                        output += """<td><b>ONLY FAILED: %s</b></td>""" % n1
                    else:
                        output += """<td >--</td>"""
                        output += """<td><b>FAILED BOTH</b></td>"""
                else:
                    output += """<td>%d</td>""" % score
                    output += """<td><b>%s</b></td>""" % winner

                output += """</tr>\n"""

        output += "\n\n</table></body></html>"

        return output


if __name__ == '__main__':
    settings = load_settings()

    stats_dir = settings['stats_archive_dir']
    replays_dir = settings['replays_archive_dir']
    logs_dir = settings['logs_archive_dir']

    html_generator = HtmlGenerator(settings['www_dir'], settings['organizer'])

    if stats_dir is not None:
        pattern = re.compile(r'stats_([-+0-9T:.]+)\.json')

        # Collect all files in stats directory
        all_files = [f for f in os.listdir(stats_dir) if os.path.isfile(os.path.join(stats_dir, f))]

        # make paths relative to www_dir
        www_dir = settings['www_dir']
        stats_dir = os.path.relpath(stats_dir, www_dir)
        replays_dir = os.path.relpath(replays_dir, www_dir) if replays_dir else None
        logs_dir = os.path.relpath(logs_dir, www_dir) if logs_dir else None

        # Process each .json stat file - 1 per contest ran
        for stats_file_name in all_files:
            match = pattern.match(stats_file_name)
            if not match:
                continue
            # Extract the id for that particular content from the stat file stats_<ID-TIMESTAMP>
            run_id = match.group(1)

            replays_file_name = f'replays_{run_id}.tar'
            logs_file_name = f'logs_{run_id}.tar'

            stats_file_full_path = os.path.join(stats_dir, stats_file_name)
            replays_file_full_path = os.path.join(replays_dir, replays_file_name) if replays_dir else None
            logs_file_full_path = os.path.join(logs_dir, logs_file_name) if logs_dir else None

            replays_file_full_path += '.gz' if not os.path.exists(replays_file_full_path) else ''
            logs_file_full_path += '.gz' if not os.path.exists(logs_file_full_path) else ''

            html_generator.add_run(run_id, stats_file_full_path, replays_file_full_path, logs_file_full_path)
