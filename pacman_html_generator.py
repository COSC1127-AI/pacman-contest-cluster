#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Generates the HTML output given logs of the past tournament runs.
"""

#  ----------------------------------------------------------------------------------------------------------------------
# Import future stuff (syntax equivalent to Python 3)

from __future__ import print_function

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
from pytz import timezone

# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG, datefmt='%a, %d %b %Y %H:%M:%S')
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                    datefmt='%a, %d %b %Y %H:%M:%S')


# ----------------------------------------------------------------------------------------------------------------------
# Load settings either from config.json or from the command line

def load_settings():
    DEFAULT_CONFIG_FILE = 'config.json'

    parser = argparse.ArgumentParser(
        description='This script generates the HTML structure given the logs of all the runs of this tournament.'
    )

    parser.add_argument(
        '--config-file',
        help='configuration file to use (default: {default})'.format(default=DEFAULT_CONFIG_FILE),
    )
    parser.add_argument(
        '--organizer',
        help='name of the organizer of the contest'
    )
    parser.add_argument(
        '--stats-archive-dir',
        help='stats directory (default <www-dir>/stats-archive)'
    )
    parser.add_argument(
        '--replays-archive-dir',
        help='replays directory (default <www-dir>/replays-archive)'
    )
    parser.add_argument(
        '--logs-archive-dir',
        help='logs directory (default <www-dir>/logs-archive)'
    )
    parser.add_argument(
        '--www-dir',
        help='output directory'
    )
    parser.add_argument(
        '--upload-www-replays',
        help='if passed it uploads recorded_games.tar into https://transfer.sh. This avoids filling up your personal www available space where data is uploaded',
        action='store_true',
    )

    args = parser.parse_args()

    # First get the options from the configuration file if available
    if not args.config_file is None:
        if os.path.exists(args.config_file):
            with open(args.config_file, 'r') as f:
                settings = json.load(f)
                logging.debug('Configuration file loaded')
        else:
            logging.error('Configuration file selected not available')
            settings = {}
    else:
        settings = {}

    # if given, set the parameters as per command line options (may override config file)
    if args.organizer:
        settings['organizer'] = args.organizer
    if args.www_dir:
        settings['www_dir'] = args.www_dir

    missing_parameters = {'organizer', 'www_dir'} - set(settings.keys())
    if missing_parameters:
        logging.error('Missing parameters: %s. Aborting.' % list(sorted(missing_parameters)))
        parser.print_help()
        sys.exit(1)

    if args.stats_archive_dir:
        settings['stats_archive_dir'] = args.stats_archive_dir
    else:
        settings['stats_archive_dir'] = os.path.join(settings['www_dir'], 'stats-archive')
    if args.replays_archive_dir:
        settings['replays_archive_dir'] = args.replays_archive_dir
    else:
        settings['replays_archive_dir'] = os.path.join(settings['www_dir'], 'replays-archive')
    if args.logs_archive_dir:
        settings['logs_archive_dir'] = args.logs_archive_dir
    else:
        settings['logs_archive_dir'] = os.path.join(settings['www_dir'], 'logs-archive')

    logging.info('Script will run with this configuration: %s' % settings)

    return settings


# ----------------------------------------------------------------------------------------------------------------------

class HtmlGenerator:
    ERROR_SCORE = 9999
    RESULTS_DIR = 'results'
    TIMEZONE = timezone('Australia/Melbourne')

    def __init__(self, www_dir, organizer):
        """
        Initializes this generator.

        :param www_dir: the output path
        :param organizer: the name of the organizer of the tournament (e.g., XX University)
        """

        # path that contains files that make-up a html navigable web folder
        self.www_dir = www_dir

        # just used in html as a readable string
        self.organizer = organizer


    def _close(self):
        pass

    def clean_up(self):
        """
        Empties and removes the output directory
        """
        shutil.rmtree(self.www_dir)

    def add_run(self, run_id, stats_file_full_path, replays_url, logs_url):
        """
        (Re)Generates the HTML for the given run and updates the HTML index.
        :return:
        """
        self._save_run_html(run_id, stats_file_full_path, replays_url, logs_url)
        self._generate_main_html()

    def _save_run_html(self, run_id, stats_file_url, replays_file_url, logs_file_url):
        """
        Generates the HTML of a contest run and saves it in www/results_<run_id>/results.html.

        The URLs passed should be either:
         - HTTP URLs, in which case the stats file is downloaded to generate the HTML
         - local relative paths, which are assumed to start from self.www_dir

        No checks are done, so mind your parameters.
        """
        html_parent_path = os.path.join(self.www_dir, 'results_%s' % run_id)

        if stats_file_url.startswith('http'):  # http url
            try:
                # Python 2.x
                import urllib.request as request
            except ImportError:
                # Python 3.x
                from urllib2 import urlopen as request
            content = request(stats_file_url).read()
            data = json.loads(content)

        else:  # relative path
            # prepend www/ so the file can be opened by this script, which is somewhere else
            stats_file_path = os.path.join(self.www_dir, stats_file_url)

            with open(stats_file_path, 'r') as f:
                data = json.load(f)

        games = data['games']
        max_steps = data['max_steps']
        team_stats = data['team_stats']
        random_layouts = data['random_layouts']
        fixed_layouts = data['fixed_layouts']

        # prepend ../ to local URLs so the files can be linked to from www/results_xxx/results.html
        if not stats_file_url.startswith('http'):  # http url
            stats_file_url = os.path.join('..', stats_file_url)
        if not replays_file_url.startswith('http'):  # http url
            replays_file_url = os.path.join('..', replays_file_url)
        if not logs_file_url.startswith('http'):  # http url
            logs_file_url = os.path.join('..', logs_file_url)

        if not os.path.exists(self.www_dir):
            os.makedirs(self.www_dir)
        contest_zip_file = zipfile.ZipFile("fonts.zip")
        contest_zip_file.extractall(self.www_dir)
        shutil.copy("style.css", self.www_dir)

        if not os.path.exists(html_parent_path):
            os.makedirs(html_parent_path)
        run_html = self._generate_output(run_id, games, team_stats, random_layouts, fixed_layouts, max_steps,
                                         stats_file_url, replays_file_url, logs_file_url)

        html_full_path = os.path.join(html_parent_path, 'results.html')
        with open(html_full_path, "w") as f:
            print(run_html, file=f)

    def _generate_main_html(self):
        """
        Generates the index HTML, containing links to the HTML files of all the runs.
        The file is saved in www/results.html.
        """
        # regenerate main html
        main_html = """<html><head><title>Results for PACMAN Capture the Flag the tournament</title>"""
        main_html += """<link rel="stylesheet" type="text/css" href="style.css"/></head>"""
        main_html += """<body><h1>Results Pacman Capture the Flag by Date</h1>"""
        main_html += """<body><h2>Organizer: %s </h1>""" % self.organizer
        for d in sorted(os.listdir(self.www_dir)):
            if not os.path.isdir(os.path.join(self.www_dir, d)):
                continue
            if d.endswith('fonts'):
                continue
            if not d.startswith('results'):
                continue
            main_html += """<a href="%s/results.html"> %s  </a> <br/>""" % (d, d)
        main_html += "<br/></body></html>"
        with open(os.path.join(self.www_dir, 'results.html'), "w") as f:
            print(main_html, file=f)

    def _generate_output(self, run_id, games, team_stats, random_layouts, fixed_layouts, max_steps,
                         stats_url, replays_url, logs_url):
        """
        Generates the HTML of the report of the run.
        """

        output = """<html><head><title>Results for the tournament round</title>"""
        output += """<link rel="stylesheet" type="text/css" href="../style.css"/></head>"""
        output += """<body><h1>PACMAN Capture the Flag Tournament</h1>"""
        output += """<body><h2>Tournament Organizer: %s </h1>""" % self.organizer
        output += """<body><h2>Date of Tournament: %s </h1>""" % run_id

        output += """<h2>Configuration: %d teams in %d (%d fixed + %d random) layouts for %d steps</h2>""" \
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
            output += """<th>Points</th>"""
            output += """<th>Win</th>"""
            output += """<th>Tie</th>"""
            output += """<th>Lost</th>"""
            output += """<th>TOTAL</th>"""
            output += """<th>FAILED</th>"""
            output += """<th>Score Balance</th>"""
            output += """</tr>"""

            # Sort teams by points v[0], then
            sorted_team_stats = sorted(team_stats.items(), key=lambda (k, v): (v[0], v[1], v[5]), reverse=True)
            position = 0
            for key, (points, wins, draws, losses, errors, sum_score) in sorted_team_stats:
                position += 1
                output += """<tr>"""
                output += """<td>%d</td>""" % position
                output += """<td>%s</td>""" % key
                output += """<td>%d</td>""" % points
                output += """<td>%d</td>""" % wins
                output += """<td >%d</td>""" % draws
                output += """<td>%d</td>""" % losses
                output += """<td>%d</td>""" % (wins + draws + losses)
                output += """<td >%d</td>""" % errors
                output += """<td >%d</td>""" % sum_score
                output += """</tr>"""
            output += "</table>"

            # Second, print each game result
            output += "<br/><br/><h2>Games</h2><br/>"
            if replays_url:
                output += """<a href="%s">DOWNLOAD REPLAYS</a><br/>""" % replays_url
            if logs_url:
                output += """<a href="%s">DOWNLOAD LOGS</a><br/>""" % logs_url
            if stats_url:
                output += """<a href="%s">DOWNLOAD STATS</a><br/>""" % stats_url
            output += """<table border="1">"""
            output += """<tr><th>Team1</th>"""
            output += """<th>Team2</th>"""
            output += """<th>Layout</th>"""
            output += """<th>Score</th>"""
            output += """<th>Winner</th></tr>"""
            for (n1, n2, layout, score, winner) in games:
                output += """<tr><td align="center">"""
                if winner == n1:
                    output += "<b>%s</b>" % n1
                else:
                    output += "%s" % n1
                output += """</td><td align="center">"""
                if winner == n2:
                    output += "<b>%s</b>" % n2
                else:
                    output += "%s" % n2
                output += """</td>"""
                if score == self.ERROR_SCORE:
                    if winner == n1:
                        output += """<td>%s</td>""" % layout
                        output += """<td >--</td>"""
                        output += """<td><b>ONLY FAILED: %s</b></td></tr>""" % n2
                    elif winner == n2:
                        output += """<td>%s</td>""" % layout
                        output += """<td >--</td>"""
                        output += """<td><b>ONLY FAILED: %s</b></td></tr>""" % n1
                    else:
                        output += """<td>%s</td>""" % layout
                        output += """<td >--</td>"""
                        output += """<td><b>FAILED BOTH</b></td></tr>"""
                else:
                    output += """<td>%s</td>""" % layout
                    output += """<td >%d</td>""" % score
                    output += """<td><b>%s</b></td></tr>""" % winner

        output += "</table></body></html>"

        return output


if __name__ == '__main__':
    settings = load_settings()

    stats_dir = settings['stats_archive_dir']
    replays_dir = settings['replays_archive_dir']
    logs_dir = settings['logs_archive_dir']

    settings = {
        'www_dir': settings['www_dir'],
        'organizer': settings['organizer'],
    }
    generator = HtmlGenerator(**settings)

    if stats_dir is not None:
        pattern = re.compile(r'stats_([-+0-9T:.]+)\.json')

        all_files = [f for f in os.listdir(stats_dir) if os.path.isfile(os.path.join(stats_dir, f))]

        # make paths relative to www_dir
        www_dir = settings['www_dir']
        stats_dir = os.path.relpath(stats_dir, www_dir)
        replays_dir = os.path.relpath(replays_dir, www_dir) if replays_dir else None
        logs_dir = os.path.relpath(logs_dir, www_dir) if logs_dir else None

        for stats_file_name in all_files:
            match = pattern.match(stats_file_name)
            if not match:
                continue
            run_id = match.group(1)
            replays_file_name = 'replays_%s.tar' % run_id
            logs_file_name = 'logs_%s.tar' % run_id

            stats_file_full_path = os.path.join(stats_dir, stats_file_name)
            replays_file_full_path = os.path.join(replays_dir, replays_file_name) if replays_dir else None
            logs_file_full_path = os.path.join(logs_dir, logs_file_name) if logs_dir else None

            replays_file_full_path += '.gz' if not os.path.exists(replays_file_full_path) else ''
            logs_file_full_path += '.gz' if not os.path.exists(logs_file_full_path) else ''

            generator.add_run(run_id, stats_file_full_path, replays_file_full_path, logs_file_full_path)
