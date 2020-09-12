#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script is to run a tournament between teams of agents for the Pacman package developed by
John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.

After running the tournament, the script generates a report in HTML. The report is, optionally,
uploaded to a specified server via scp.
                    
The script was developed for RMIT COSC1125/1127 AI course in Semester 1, 2017 by A/Prof. Sebastian Sardina and PhD
student Marco Tamassia. The script is in turn based on an original script from Dr. Nir Lipovetzky.
"""
#from __future__ import print_function
# from sqlalchemy.sql.functions import random

__author__ = "Sebastian Sardina, Marco Tamassia, and Nir Lipovetzky"
__copyright__ = "Copyright 2017-2020"
__license__ = "GPLv3"

import os
import re
import sys
import datetime
import argparse
import json
import shutil
import zipfile
import logging
import glob
import csv
import random
# noinspection PyCompatibility
#import commands
import tarfile
import subprocess
import iso8601
from itertools import combinations
from cluster_manager import ClusterManager, Job, Host, TransferableFile
from pytz import timezone

#import cluster_manager
from pacman_html_generator import HtmlGenerator

# check https://stackoverflow.com/questions/10677721/advantages-of-logging-vs-print-logging-best-practices
# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG, datefmt='%a, %d %b %Y %H:%M:%S')
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                    datefmt='%a, %d %b %Y %H:%M:%S')

DIR_SCRIPT = sys.path[0]

# ----------------------------------------------------------------------------------------------------------------------
# Load settings either from config.json or from the command line

def default(str):
    return str + ' [Default: %default]'

def load_settings():
    DEFAULT_MAX_STEPS = 1200
    DEFAULT_FIXED_LAYOUTS = 3
    DEFAULT_LAYOUTS_ZIP_FILE = os.path.join(DIR_SCRIPT, 'layouts.zip')
    DEFAULT_RANDOM_LAYOUTS = 3
    DEFAULT_CONFIG_FILE = 'config.json'


    parser = argparse.ArgumentParser(
        description='This script is to run a tournament between teams of agents for the Pacman package developed by '
                    'John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.\n'
                    '\n'
                    'After running the tournament, the script generates a report in HTML. The report is, optionally, '
                    'uploaded to a specified server via scp.\n'
                    '\n'
                    'The parameters are saved in config.json, so it is only necessary to pass them the first time or '
                    'if they have to be updated.\n'
                    '\n'
                    'The script was developed for RMIT COSC1125/1127 AI course in 2017 (A/Prof. Sebastian Sardina), '
                    'and is based on an original script from Dr. Nir Lipovetzky for UoM COMP90054.'
                    'From 2017 both have been developing futher this tool.'
    )

    parser.add_argument(
        '--config-file',
        help='configuration file to use (default: %(default)s).',
        default = DEFAULT_CONFIG_FILE
    )
    parser.add_argument(
        '--organizer',
        help='name of contest organizer (default: %(default)s).',
        default = 'Uni Pacman'
    )
    parser.add_argument(
        '--www-dir',
        help='www output directory.'
    )
    parser.add_argument(
        '--stats-archive-dir',
        help='stats archive output directory.'
    )
    parser.add_argument(
        '--replays-archive-dir',
        help='replays archive output directory.'
    )
    parser.add_argument(
        '--logs-archive-dir',
        help='logs archive output directory.'
    )
    parser.add_argument(
        '--compress-logs',
        help='compress logs in a tar.gz file (otherwise, logs will be archived in a tar file).',
        action='store_true'
    )
    parser.add_argument(
        '--workers-file',
        help='json file with workers details.'
    )
    parser.add_argument(
        '--teams-root',
        help='directory containing the zip files or directories of the teams. See README for format on names.'
    )
    parser.add_argument(
        '--team-names-file',
        help='the path of the csv that contains (at least) two columns headed "STUDENT_ID" and "TEAM_NAME", used to match'
             ' submissions with teams. If passed, files/dirs have to be of a certain format <student no>_TIMESTAMP.zip'
             ' If no file is specified, team file/dir will be used as name and all will be included.'
    )
    parser.add_argument(
        '--staff-teams-dir',
        help='if given, include staff teams in the given directory (with name staff_team_xxxx.zip).'
    )
    parser.add_argument(
        '--staff-teams-vs-others-only',
        help='if set to true, it will create only games for each student team vs the staff teams. This is useful to provide fast feedback, as it avoids playing student teams in the same game. ',
        action='store_true',
    )
    parser.add_argument(
        '--max-steps',
        help='the limit on the number of steps for each game (default: %(default)s).',
        default=DEFAULT_MAX_STEPS
    )
    parser.add_argument(
        '--no-fixed-layouts',
        help='number of (random) layouts to use from a given fix set (default: %(default)s).',
        default=DEFAULT_FIXED_LAYOUTS,
    )
    parser.add_argument(
        '--fixed-layout-seeds',
        help='Name of fixed layouts to be included separated by commas, e.g., contest02cCapture,contest12Capture.',
    )
    parser.add_argument(
        '--fixed-layouts-file',
        help='zip file where all fixed layouts are stored (default: %(default)s).',
        default=DEFAULT_LAYOUTS_ZIP_FILE,
    )
    parser.add_argument(
        '--no-random-layouts',
        help='number of random layouts to use (default: %(default)s).',
        default=DEFAULT_RANDOM_LAYOUTS,
    )
    parser.add_argument(
        '--random-seeds',
        help='random seeds for random layouts to use, separated by commas. Eg. 1,2,3.',
    )
    parser.add_argument(
        '--resume-competition-folder',
        help='directory containing the logs and replays from the last failed competition. Can be found in /tmp folder. Rename it to use the folder as an argument.',
        default='',
    )    
    parser.add_argument(
        '--allow-non-registered-students',
        help='if passed and --team-names-file is given, students without a team are still allowed to participate',
        action='store_true',
    )
    parser.add_argument(
        '--build-config-file',
        help='if passed, config.json file will be generated with current options',
        action='store_true',
    )
    parser.add_argument(
        '--upload-replays',
        help='upload replays to https://transfer.sh',
        action='store_true',
    )
    parser.add_argument(
        '--upload-logs',
        help='upload logs to https://transfer.sh',
        action='store_true',
    )
    parser.add_argument(
        '--upload-all',
        help='uploads logs and replays into https://transfer.sh.',
        action='store_true',
    )

    #TODO: This can be replaced with settings = vars(parser.parse_args()) to generate settings right away!
    # we would have to also set the types of arguments above, for example integers
    args = parser.parse_args()

    # If no arguments are given, stop
    if len(sys.argv) == 1:
        print('No arguments given. Use -h fo help')
        sys.exit(0)

    # First get the options from the configuration file if available
    if not args.config_file is None:
        if os.path.exists(args.config_file):
            with open(args.config_file, 'r') as f:
                settings = json.load(f)
                logging.debug('Configuration file loaded')
        else:
            logging.warning('Configuration file not available.')
            settings = {}
    else:
        settings = {}

    # if given, set the parameters as per command line options (may override config file)
    if args.organizer:
        settings['organizer'] = args.organizer

    if args.www_dir:
        settings['www_dir'] = args.www_dir
    if args.compress_logs:
        settings['compress_logs'] = args.compress_logs
    if args.workers_file:
        settings['workers_file'] = args.workers_file

    if args.resume_competition_folder:
        settings['resume_competition_folder'] = args.resume_competition_folder
    else:
        settings['resume_competition_folder'] = ''
        
    if args.staff_teams_dir:
        settings['staff_teams_dir'] = args.staff_teams_dir
        settings['include_staff_team'] = True
    else:
        settings['include_staff_team'] = False
        settings['staff_teams_dir'] = 'None'

    if args.staff_teams_vs_others_only:
        settings['staff_teams_vs_others_only'] = True
    else:
        settings['staff_teams_vs_others_only'] = False
        
    if args.teams_root:
        settings['teams_root'] = args.teams_root
    if args.team_names_file:
        settings['team_names_file'] = args.team_names_file
        settings['ignore_file_name_format'] = False
    else:
        settings['ignore_file_name_format'] = True
        settings['team_names_file'] = 'None'

    if args.stats_archive_dir:
        settings['stats_archive_dir'] = args.stats_archive_dir
    if args.replays_archive_dir:
        settings['replays_archive_dir'] = args.replays_archive_dir
    if args.logs_archive_dir:
        settings['logs_archive_dir'] = args.logs_archive_dir

    if args.no_fixed_layouts:
        settings['no_fixed_layouts'] = int(args.no_fixed_layouts)
    if args.fixed_layout_seeds:
        settings['fixed_layout_seeds'] = [x for x in args.fixed_layout_seeds.split(',')]
    if args.no_random_layouts:
        settings['no_random_layouts'] = int(args.no_random_layouts)
    if args.random_seeds:
        settings['random_seeds'] = [int(x) for x in args.random_seeds.split(',')]
    if args.max_steps:
        settings['max_steps'] = int(args.max_steps)
    elif 'max_steps' not in set(settings.keys()):
        settings['max_steps'] = DEFAULT_MAX_STEPS

    if args.upload_all:
        settings['upload_replays'] = True
        settings['upload_logs'] = True
    else:
        settings['upload_replays'] = args.upload_replays
        settings['upload_logs'] = args.upload_logs

    settings['allow_non_registered_students'] = args.allow_non_registered_students
    settings['fixed_layouts_file'] = args.fixed_layouts_file

    missing_parameters = set({}) - set(settings.keys())
    if missing_parameters:
        logging.error('Missing parameters: %s. Aborting.' % list(sorted(missing_parameters)))
        parser.print_help()
        sys.exit(1)

    # dump current config files into configuration file if requested to do so
    if args.build_config_file:
        logging.info('Dumping current options to file %s' % args.config_file)
        with open(args.config_file, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=4, separators=(',', ': '))


    return settings


# ----------------------------------------------------------------------------------------------------------------------

class ContestRunner:

    ERROR_SCORE = 9999

    # Output directories:
    #  run_replays/{red_team_name}_vs_{blue_team_name}_{layout}.replay
    #  run_logs/{red_team_name}_vs_{blue_team_name}_{layout}.log
    #  replays_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .replay files
    #  logs_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .log files
    #  stats_archive/replays_{contest_timestamp_id}.json
    DEFAULT_STATS_ARCHIVE_DIR = 'stats-archive'
    DEFAULT_LOGS_ARCHIVE_DIR = 'logs-archive'
    DEFAULT_REPLAYS_ARCHIVE_DIR = 'replays-archive'

    TMP_DIR = 'tmp'
    TMP_CONTEST_DIR = os.path.join(TMP_DIR, 'contest-run')
    TMP_REPLAYS_DIR = os.path.join(TMP_DIR, 'replays-run')
    TMP_LOGS_DIR = os.path.join(TMP_DIR, 'logs-run')

    CONTEST_ZIP_FILE = 'contest.zip'
    STAFF_TEAM_ZIP_FILE = ['staff_team_basic.zip', 'staff_team_medium.zip', 'staff_team_top.zip']
    STAFF_TEAM_FILENAME_PATTERN = re.compile(r'^staff\_team\_.+\.zip$')
    TEAMS_SUBDIR = 'teams'
    RESULTS_DIR = 'results'
    TIMEZONE = timezone('Australia/Melbourne')
    CORE_CONTEST_TEAM_ZIP_FILE = 'contest_and_teams.zip'
    SUBMISSION_FILENAME_PATTERN = re.compile(r'^(s\d+)(_([-+0-9T:.]+))?(\.zip)?$')

    # submissions file format: s???????[_datetime].zip
    # submissions folder format: s???????[_datetime]
    # datetime in ISO8601 format:  https://en.wikipedia.org/wiki/ISO_8601
    def __init__(self, organizer, teams_root, staff_teams_vs_others_only, include_staff_team, staff_teams_dir, compress_logs,
                 max_steps, no_fixed_layouts,
                 fixed_layouts_file, no_random_layouts, team_names_file,
                 allow_non_registered_students, ignore_file_name_format, www_dir,
                 fixed_layout_seeds=[], random_seeds=[],
                 stats_archive_dir=None, logs_archive_dir=None, replays_archive_dir=None,
                 upload_replays=False, upload_logs=False):

        self.organizer = organizer
        self.max_steps = max_steps

        self.www_dir = www_dir
        self.stats_archive_dir = \
            os.path.join(self.www_dir, stats_archive_dir or self.DEFAULT_STATS_ARCHIVE_DIR)
        self.logs_archive_dir = \
            os.path.join(self.www_dir, logs_archive_dir or self.DEFAULT_LOGS_ARCHIVE_DIR)
        self.replays_archive_dir = \
            os.path.join(self.www_dir, replays_archive_dir or self.DEFAULT_REPLAYS_ARCHIVE_DIR)

        self.upload_replays = upload_replays
        self.upload_logs = upload_logs

        # self.maxTimeTaken = Null

        # flag indicating the contest only will run student teams vs staff teams, instead of a full tournament
        self.staff_teams_vs_others_only = staff_teams_vs_others_only

        # unique id for this execution of the contest; used to label logs
        self.contest_timestamp_id = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")

        # a flag indicating whether to compress the logs
        self.compress_logs = compress_logs

        if not os.path.exists(os.path.join(DIR_SCRIPT, self.CONTEST_ZIP_FILE)):
            logging.error('File %s could not be found. Aborting.' % self.CONTEST_ZIP_FILE)
            sys.exit(1)

        if not fixed_layouts_file:
            logging.error('File %s could not be found. Aborting.' % fixed_layouts_file)
            sys.exit(1)

        # Setup Pacman CTF environment by extracting it from a clean zip file
        self.layouts = None
        self._prepare_platform(os.path.join(DIR_SCRIPT, self.CONTEST_ZIP_FILE), fixed_layouts_file, self.TMP_CONTEST_DIR, no_fixed_layouts,
                               no_random_layouts, fixed_layout_seeds, random_seeds)

        # Report layouts to be played, fixed and random (with seeds)
        logging.info('Layouts to be played: %s' % self.layouts)
        random_layouts_selected = set([x for x in self.layouts if re.compile(r'RANDOM[0-9]*').match(x)])
        fixed_layouts_selected = self.layouts.difference(random_layouts_selected)

        seeds_strings = [m.group(1) for m in (re.compile(r'RANDOM([0-9]*)').search(layout) for layout in random_layouts_selected)
                 if m]
        seeds = list(map(lambda x: int(x), seeds_strings))
        logging.info('Seeds for RANDOM layouts to be played: %s' % seeds)
        logging.info('Seeds for FIXED layouts to be played: %s' % ','.join(fixed_layouts_selected))

        # Setup all of the TEAMS
        teams_dir = os.path.join(self.TMP_CONTEST_DIR, self.TEAMS_SUBDIR)
        if os.path.exists(teams_dir):
            shutil.rmtree(teams_dir)
        os.makedirs(teams_dir)

        if os.path.exists(self.TMP_REPLAYS_DIR):
            shutil.rmtree(self.TMP_REPLAYS_DIR)
        os.makedirs(self.TMP_REPLAYS_DIR)

        if os.path.exists(self.TMP_LOGS_DIR):
            shutil.rmtree(self.TMP_LOGS_DIR)
        os.makedirs(self.TMP_LOGS_DIR)

        # Get all team name mapping from mapping file, If no file is specified, all zip files in team folder will be taken.
        if team_names_file is 'None':
            self.team_names = None
        else:
            self.team_names = self._load_teams(team_names_file)

        # setup all team directories under contest/team subdir for contest (copy content in .zip to team dirs)
        self.teams = []
        self.staff_teams = []
        self.submission_times = {}

        for submission_file in os.listdir(teams_root):
            submission_path = os.path.join(teams_root, submission_file)
            if submission_file.endswith(".zip") or os.path.isdir(submission_path):
                self._setup_team(submission_path, teams_dir, ignore_file_name_format,
                                 allow_non_registered_students=allow_non_registered_students)


        # Include staff teams if available (ones with pattern STAFF_TEAM_FILENAME_PATTERN)
        if include_staff_team:
            for staff_team_submission_file in os.listdir(staff_teams_dir):
                match = re.match(self.STAFF_TEAM_FILENAME_PATTERN, os.path.basename(staff_team_submission_file))
                if match:
                    submission_path = os.path.join(staff_teams_dir, staff_team_submission_file)
                    if staff_team_submission_file.endswith(".zip") or os.path.isdir(submission_path):
                        self._setup_team(submission_path, teams_dir, True, False, True )

        # # Add the staff team, if necessary
        # if include_staff_team:
        #     for STAFF_TEAM in [os.path.join(staff_teams_dir, staff_file) for staff_file in self.STAFF_TEAM_ZIP_FILE]:
        #         if not os.path.exists(STAFF_TEAM):
        #             logging.error('Staff team file %s could not be found. Aborting.' % STAFF_TEAM)
        #             sys.exit(1)
        #         self._setup_team(STAFF_TEAM, teams_dir, True)

        # zip directory for transfer to remote workers
        shutil.make_archive(self.CORE_CONTEST_TEAM_ZIP_FILE[:-4], 'zip', self.TMP_CONTEST_DIR)

        self.ladder = {n: [] for n, _ in self.teams}
        self.games = []
        self.errors = {n: 0 for n, _ in self.teams}
        self.team_stats = {n: 0 for n, _ in self.teams}

    def _close(self):
        pass

    def clean_up(self):
        pass
        # shutil.rmtree(self.TMP_DIR)

    def _parse_result(self, output, red_team_name, blue_team_name, layout):
        """
        Parses the result log of a match.
        :param output: an iterator of the lines of the result log
        :param red_team_name: name of Red team
        :param blue_team_name: name of Blue team
        :return: a tuple containing score, winner, loser and a flag signalling whether there was a bug
        """
        score = 0
        winner = None
        loser = None
        bug = False
        tied = False
        totaltime = 0

        try:
            output = output.decode()    # convert byte into string
        except:
            pass    # it is already a string
        
        if output.find("Traceback") != -1 or output.find("agent crashed") != -1:
            bug = True
            # if both teams fail to load, no one wins
            if output.find("Red team failed to load!") != -1 and output.find("Blue team failed to load!") != -1:
                self.errors[red_team_name] += 1
                self.errors[blue_team_name] += 1
                winner = None
                loser = None
                score = self.ERROR_SCORE
            elif output.find("Red agent crashed") != -1 or output.find("redAgents = loadAgents") != -1 or output.find(
                    "Red team failed to load!") != -1:
                self.errors[red_team_name] += 1
                winner = blue_team_name
                loser = red_team_name
                score = 1
            elif output.find("Blue agent crashed") != -1 or output.find("blueAgents = loadAgents") != -1 or output.find(
                    "Blue team failed to load!"):
                self.errors[blue_team_name] += 1
                winner = red_team_name
                loser = blue_team_name
                score = 1
            else:
                logging.error(
                    "Note able to parse out for game {} vs {} in {} (traceback available, but couldn't get winner!)".format(
                        red_team_name, blue_team_name, layout))
        else:
            for line in output.splitlines():
                if line.find("wins by") != -1:
                    score = abs(int(line.split('wins by')[1].split('points')[0]))
                    if line.find('Red') != -1:
                        winner = red_team_name
                        loser = blue_team_name
                    elif line.find('Blue') != -1:
                        winner = blue_team_name
                        loser = red_team_name
                if line.find("The Blue team has returned at least ") != -1:
                    score = abs(int(line.split('The Blue team has returned at least ')[1].split(' ')[0]))
                    winner = blue_team_name
                    loser = red_team_name
                elif line.find("The Red team has returned at least ") != -1:
                    score = abs(int(line.split('The Red team has returned at least ')[1].split(' ')[0]))
                    winner = red_team_name
                    loser = blue_team_name
                elif line.find("Tie Game") != -1 or line.find("Tie game") != -1:
                    winner = None
                    loser = None
                    tied = True

                if line.find("Total Time Game: ") != -1:
                    totaltime = int(float(line.split('Total Time Game: ')[1].split(' ')[0]))

            # signal strange case where script was unable to find outcome of game - should never happen!
            if winner is None and loser is None and not tied:
                logging.error(
                    "Note able to parse out for game {} vs {} in {} (no traceback available)".format(
                        red_team_name, blue_team_name, layout))
                print(output)
                winner = None
                loser = None
                tied = True
                score = -1
                # sys.exit(1)

        return score, winner, loser, bug, totaltime

    def _prepare_platform(self, contest_zip_file_path, layouts_zip_file_path, destination, no_fixed_layouts, no_random_layouts, fixed_layout_seeds=[], random_seeds=[]):
        """
        Cleans the given destination directory and prepares a fresh setup to execute a Pacman CTF game within.
        Information on the layouts are saved in the member variable layouts.
        
        :param contest_zip_file_path: the zip file containing the necessary files for the contest (no sub-folder).
        :param layouts_zip_file_path: the zip file containing the layouts to be used for the contest (in the root).
        :param destination: the directory in which to setup the environment.
        :returns: a list of all the layouts
        """
        if os.path.exists(destination):
            shutil.rmtree(destination)
        os.makedirs(destination)
        contest_zip_file = zipfile.ZipFile(contest_zip_file_path)
        contest_zip_file.extractall(os.path.join(self.TMP_CONTEST_DIR, '.'))
        layouts_zip_file = zipfile.ZipFile(layouts_zip_file_path)
        layouts_zip_file.extractall(os.path.join(self.TMP_CONTEST_DIR, 'layouts'))


        # Pick no_fixed_layouts layouts from the given set in the layout zip file
        #   if layout seeds have been given use them
        layouts_available = set([file_in_zip[:-4] for file_in_zip in layouts_zip_file.namelist()])
        fixed_layout_seeds = set(fixed_layout_seeds)
        random_seeds = set(random_seeds)

        if no_fixed_layouts > len(layouts_available):
            logging.error(
                'There are not enough fixed layout (asked for %d layouts, but there are only %d).' % (
                no_fixed_layouts, len(layouts_available)))
            exit(1)
        if len(fixed_layout_seeds) > no_fixed_layouts:
            logging.error(
                'Too many fixed seeds layouts selected (%d) for a total of %d fixed layouts requested to play.' % (
                    len(fixed_layout_seeds), no_fixed_layouts))
            exit(1)
        if not fixed_layout_seeds.issubset(layouts_available):  # NOT empty, list of layouts provided
            logging.error('There are fixed layout seeds  that are not available: %s.' % fixed_layout_seeds.difference(
                layouts_available))
            exit(1)

        # assign the set of fixed layouts to be used: the seeds given and complete with random picks from available
        self.layouts = fixed_layout_seeds.union(
            random.sample(layouts_available.difference(fixed_layout_seeds), no_fixed_layouts - len(fixed_layout_seeds)))

        # Next, pick the random layouts, and included all the seeds provided if any
        if len(random_seeds) > no_random_layouts:
            logging.error(
                'Too many random seeds layouts selected (%d) for a total of %d random layouts requested to play.' % (
                    len(fixed_layout_seeds), no_fixed_layouts))
            exit(1)

        # complete the mising random layouts
        self.layouts = self.layouts.union(set(['RANDOM%s' % x for x in random_seeds])) # add random seeds given, if any
        while len(self.layouts) < no_random_layouts + no_fixed_layouts:
            self.layouts.add('RANDOM%s' % str(random.randint(1, 9999)))


    def _setup_team(self, submission_path, destination, ignore_file_name_format=False,
                    allow_non_registered_students=False, is_staff_team=False):
        """
        Extracts team.py from the team submission zip file into a directory inside contest/teams
            If the zip file name is listed in team-name mapping, then name directory with team name
            otherwise name directory after the zip file.
        Information on the teams are saved in the member variable teams.
        
        :param submission_path: the zip file or directory of the team.
        :param destination: the directory where the team directory is to be created and files copied.
        :param ignore_file_name_format: if True, an invalid file name format does not cause the team to be ignored.
        In this case, if the file name truly is not respecting the format, the zip file name (minus the .zip part) is
        used as team name. If this function is called twice with files having the same name (e.g., if they are in
        different directories), only the first one is kept.
        :param allow_non_registered_students: if True, students not appearing in the team_names are still allowed (team
        name used is the student id).
        :raises KeyError if the zip file contains multiple copies of team.py, non of which is in the root.
        """
        if os.path.isdir(submission_path):
            submission_zip_file = None
        else:
            try:
                submission_zip_file = zipfile.ZipFile(submission_path)
            except zipfile.BadZipfile:
                logging.warning('Submission is not a valid ZIP file nor a folder: %s. Skipping' % submission_path)
                return

        # Get team name from submission: if in self.team_names mapping, then use mapping; otherwise use filename
        match = re.match(self.SUBMISSION_FILENAME_PATTERN, os.path.basename(submission_path))
        submission_time = None
        if match:
            student_id = match.group(1)

            # first get the team of this submission
            if student_id in self.team_names:
                team_name = self.team_names[student_id]
            elif allow_non_registered_students:
                team_name = student_id
            else:
                logging.warning('Student not registered: "%s" (file %s). Skipping' % (student_id, submission_path))
                return

            # next get the submission date (encoded in filename)
            try:
                submission_time = iso8601.parse_date(match.group(3)).astimezone(self.TIMEZONE)
            except iso8601.iso8601.ParseError:
                if not ignore_file_name_format:
                    logging.warning('Team zip file "%s" name has invalid date format. Skipping' % submission_path)
                    return
        else:
            if not ignore_file_name_format:
                logging.warning('Submission zip file "%s" does not correspond to any team. Skipping' % submission_path)
                return
            team_name = os.path.basename(submission_path)
            team_name = team_name[:-4] if team_name.endswith(".zip") else team_name

        # This submission will be temporarily expanded into team_destination_dir
        team_destination_dir = os.path.join(destination, team_name)
        desired_file = 'myTeam.py'

        if team_name not in self.submission_times:
            if submission_zip_file is None:
                shutil.copytree(submission_path, team_destination_dir)
            else:
                submission_zip_file.extractall(team_destination_dir)
            agent_factory = os.path.join(self.TEAMS_SUBDIR, team_name, desired_file)
            if is_staff_team:
                self.staff_teams.append((team_name, agent_factory))
            self.teams.append((team_name, agent_factory))
            self.submission_times[team_name] = submission_time

        elif submission_time is not None and self.submission_times[team_name] < submission_time:
            shutil.rmtree(team_destination_dir)
            if submission_zip_file is None:
                shutil.copy(submission_path, team_destination_dir)
            else:
                submission_zip_file.extractall(team_destination_dir)
            self.submission_times[team_name] = submission_time

    def _generate_command(self, red_team, blue_team, layout):
        (red_team_name, red_team_agent_factory) = red_team
        (blue_team_name, blue_team_agent_factory) = blue_team
        # TODO: make the -c an option at the meta level to "Catch exceptions and enforce time limits"
        command = 'python3 capture.py -c -r "{red_team_agent_factory}" -b "{blue_team_agent_factory}" -l {layout} -i {steps} -q --record --recordLog --delay 0.0'.format(
            red_team_agent_factory=red_team_agent_factory, blue_team_agent_factory=blue_team_agent_factory,
            layout=layout, steps=self.max_steps)
        return command

    def _analyse_output(self, red_team, blue_team, layout, exit_code, output, total_secs_taken):
        """
        Analyzes the output of a match and updates self.games accordingly.
        """
        (red_team_name, red_team_agent_factory) = red_team
        (blue_team_name, blue_team_agent_factory) = blue_team

        # dump the log of the game into file for the game: red vs blue in layout
        log_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.log'.format(
            layout=layout, run_id=self.contest_timestamp_id, red_team_name=red_team_name, blue_team_name=blue_team_name)
        # results/results_<run_id>/{red_team_name}_vs_{blue_team_name}_{layout}.log
        if output is not None:
            with open(os.path.join(self.TMP_LOGS_DIR, log_file_name), 'w') as f:
                try:
                    print(output.decode('utf-8'), file=f)
                except:
                    print(output, file=f)

        else:
            with open(os.path.join(self.TMP_LOGS_DIR, log_file_name), 'r') as f:
                try:
                    output = f.read()
                except:
                    output = ''

        if exit_code == 0:
            pass
            # print(
            #     ' Successful: Log in {output_file}.'.format(output_file=os.path.join(self.TMP_LOGS_DIR, log_file_name)))
        else:
            print('Game Failed: Check log in {output_file}.'.format(output_file=log_file_name))

        score, winner, loser, bug, totaltime = self._parse_result(output, red_team_name, blue_team_name, layout)

        if winner is None:
            self.ladder[red_team_name].append(score)
            self.ladder[blue_team_name].append(score)
        else:
            self.ladder[winner].append(score)
            self.ladder[loser].append(-score)

        # Next handle replay file
        replay_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.replay'.format(
            layout=layout, run_id=self.contest_timestamp_id, red_team_name=red_team_name, blue_team_name=blue_team_name)

        replays = glob.glob(os.path.join(self.TMP_CONTEST_DIR, 'replay*'))
        if replays:
            # results/results_<contest_timestamp_id>/{red_team_name}_vs_{blue_team_name}_{layout}.replay
            shutil.move(replays[0], os.path.join(self.TMP_REPLAYS_DIR, replay_file_name))
        if not bug:
            self.games.append((red_team_name, blue_team_name, layout, score, winner, totaltime))
        else:
            self.games.append((red_team_name, blue_team_name, layout, self.ERROR_SCORE, winner, totaltime))



    @staticmethod
    def upload_file(file_full_path, remote_name=None, remove_local=False):
        file_name = os.path.basename(file_full_path)
        remote_name = remote_name or file_name

        logging.info('Transferring %s to transfer.sh service...' % file_name)
        transfer_cmd = 'curl --upload-file %s https://transfer.sh/%s' % (file_full_path, remote_name)
        try:
            # This will yield a byte, not a str (at least in Python 3)
            transfer_url = subprocess.check_output(transfer_cmd, shell=True)
            if 'Could not save metadata' in transfer_url:
                raise ValueError('Transfer.sh returns incorrect url: %s'%transfer_url)
            if remove_local:
                print('rm %s' % file_full_path)
                os.system('rm %s' % file_full_path)
                transfer_url = transfer_url.decode() # convert to string
            logging.info(
                'File %s transfered successfully to transfer.sh service; URL: %s' % (file_name, transfer_url))
        except Exception as e:
            # If transfer failed, use the standard server
            logging.error("Transfer-url failed, using local copy to store games. Exception: %s" % str(e))
            raise
            # transfer_url = file_name

        return transfer_url

    def store_results(self):
        # Basic data stats
        data_stats = {
            'games': self.games,
            'team_stats': self.team_stats,
            'random_layouts': [l for l in self.layouts if l.startswith('RANDOM')],
            'fixed_layouts': [l for l in self.layouts if not l.startswith('RANDOM')],
            'max_steps': self.max_steps,
            'organizer' : self.organizer,
            'timestamp_id' : self.contest_timestamp_id
        }

        # Process replays: compress and upload
        replays_archive_name = 'replays_%s.tar' % self.contest_timestamp_id
        replays_archive_name += '.gz' if self.compress_logs else ''
        replays_archive_full_path = os.path.join(self.replays_archive_dir, replays_archive_name)
        with tarfile.open(replays_archive_full_path, 'w:gz' if self.compress_logs else 'w') as tar:
            tar.add(self.TMP_REPLAYS_DIR, arcname='/')
        if self.upload_replays:
            try:
                replays_file_url = self.upload_file(replays_archive_full_path, remove_local=False)
                data_stats['url_replays'] = replays_file_url.decode()
            except Exception as e:
                replays_file_url = os.path.relpath(replays_archive_full_path, self.www_dir)
        else:
            replays_file_url = os.path.relpath(replays_archive_full_path, self.www_dir)  # stats-archive/stats_xxx.json

        # Process replays: compress and upload
        logs_archive_name = 'logs_%s.tar' % self.contest_timestamp_id
        logs_archive_name += '.gz' if self.compress_logs else ''
        logs_archive_full_path = os.path.join(self.logs_archive_dir, logs_archive_name)
        with tarfile.open(logs_archive_full_path, 'w:gz' if self.compress_logs else 'w') as tar:
            tar.add(self.TMP_LOGS_DIR, arcname='/')
        if self.upload_logs:
            try:
                logs_file_url = self.upload_file(logs_archive_full_path, remove_local=False)
                data_stats['url_logs'] = logs_file_url.decode()
            except Exception as e:
                logs_file_url = os.path.relpath(logs_archive_full_path, self.www_dir)
        else:
            logs_file_url = os.path.relpath(logs_archive_full_path, self.www_dir)


        # Store stats in a json file
        stats_file_name = 'stats_%s.json' % self.contest_timestamp_id  # stats_xxx.json
        stats_file_full_path = os.path.join(self.stats_archive_dir, stats_file_name) # www/stats-archive/stats_xxx.json
        stats_file_rel_path = os.path.relpath(stats_file_full_path, self.www_dir)
        with open(stats_file_full_path, "w") as f:
            json.dump(data_stats, f)

        return stats_file_rel_path, replays_file_url, logs_file_url



    # prepare local direcotires to store replays, logs, etc.
    def prepare_dirs(self):
        if not os.path.exists(self.stats_archive_dir):
            os.makedirs(self.stats_archive_dir)
        if not os.path.exists(self.replays_archive_dir):
            os.makedirs(self.replays_archive_dir)
        if not os.path.exists(self.logs_archive_dir):
            os.makedirs(self.logs_archive_dir)

    # Generates a job to play read_team vs blue_team in layout
    def _generate_job(self, red_team, blue_team, layout):
        red_team_name, _ = red_team
        blue_team_name, _ = blue_team

        game_command = self._generate_command(red_team, blue_team, layout)

        deflate_command = 'mkdir -p {contest_dir} ; unzip -o {zip_file} -d {contest_dir} ; chmod +x -R *'.format(
            zip_file=os.path.join('/tmp', self.CORE_CONTEST_TEAM_ZIP_FILE), contest_dir=self.TMP_CONTEST_DIR)

        command = '{deflate_command} ; cd {contest_dir} ; {game_command} ; touch {replay_filename}'.format(
            deflate_command=deflate_command, contest_dir=self.TMP_CONTEST_DIR, game_command=game_command,
            replay_filename='replay-0')

        # We used to transfer contest_and_teams.zip at every job, but not anymore
        # we transfered it once at the start per machine, and just copy+unzip there directly
        # req_file = TransferableFile(local_path=self.CORE_CONTEST_TEAM_ZIP_FILE, remote_path=self.CORE_CONTEST_TEAM_ZIP_FILE)

        replay_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.replay'.format(layout=layout,
                                                                                        run_id=self.contest_timestamp_id,
                                                                                        red_team_name=red_team_name,
                                                                                        blue_team_name=blue_team_name)
        
        log_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.log'.format(
            layout=layout, run_id=self.contest_timestamp_id, red_team_name=red_team_name, blue_team_name=blue_team_name)

        ret_file_replay = TransferableFile(local_path=os.path.join(self.TMP_REPLAYS_DIR, replay_file_name),
                                    remote_path=os.path.join(self.TMP_CONTEST_DIR, 'replay-0'))
        ret_file_log = TransferableFile(local_path=os.path.join(self.TMP_LOGS_DIR, log_file_name),
                                    remote_path=os.path.join(self.TMP_CONTEST_DIR, 'log-0'))

        return Job(command=command, required_files=[], return_files=[ ret_file_replay, ret_file_log ], data=(red_team, blue_team, layout),
                   id='{}-vs-{}-in-{}'.format(red_team_name, blue_team_name, layout))

    
    # Generates a job to restore a game read_team vs blue_team in layout
    def _generate_empty_job(self, red_team, blue_team, layout):
        red_team_name, _ = red_team
        blue_team_name, _ = blue_team

        command = ''

        # We used to transfer contest_and_teams.zip at every job, but not anymore
        # we transfered it once at the start per machine, and just copy+unzip there directly
        # req_file = TransferableFile(local_path=self.CORE_CONTEST_TEAM_ZIP_FILE, remote_path=self.CORE_CONTEST_TEAM_ZIP_FILE)


        return Job(command=command, required_files=[], return_files=[  ], data=(red_team, blue_team, layout),
                   id='{}-vs-{}-in-{}'.format(red_team_name, blue_team_name, layout))


    def _analyse_all_outputs(self, results):
        logging.info('About to analyze game result outputs. Number of result output to analyze: {}'.format(len(results)))
        for result in results:
            (red_team, blue_team, layout), exit_code, output, error, total_secs_taken = result
            if not exit_code == 0:
                print('Game {} VS {} in {} exited with code {} and here is the output:'.format(red_team[0],
                                                                                               blue_team[0], layout,
                                                                                               exit_code, output))
            self._analyse_output(red_team, blue_team, layout, exit_code, None, total_secs_taken)

    def run_contest_remotely(self, hosts):
        self.prepare_dirs()

        jobs = []
        if self.staff_teams_vs_others_only:
            for red_team in self.teams:
                for blue_team in self.staff_teams:
                    if red_team in self.staff_teams: continue #do not play a staff team against another staff team
                    for layout in self.layouts:
                        jobs.append(self._generate_job(red_team, blue_team, layout))                        
        else:
            for red_team, blue_team in combinations(self.teams, r=2):
                for layout in self.layouts:
                    jobs.append(self._generate_job(red_team, blue_team, layout))


        #  This is the core package to be transferable to each host
        core_req_file = TransferableFile(local_path=os.path.join(DIR_SCRIPT, self.CORE_CONTEST_TEAM_ZIP_FILE),
                                         remote_path=os.path.join('/tmp', self.CORE_CONTEST_TEAM_ZIP_FILE))

        # create cluster with hots and jobs and run it by starting it, and then analyze output results
        # results will contain all outputs from every game played
        cm = ClusterManager(hosts, jobs, [core_req_file])
        # sys.exit(0)
        results = cm.start()

        print('========================= GAMES FINISHED - NEXT ANALYSING OUTPUT OF GAMES ========================= ')
        self._analyse_all_outputs(results)
        self._calculate_team_stats()

    def resume_contest_remotely(self, hosts, resume_folder):
        self.prepare_dirs()

        shutil.rmtree(self.TMP_LOGS_DIR)
        shutil.copytree(resume_folder + 'logs-run', self.TMP_LOGS_DIR)
        shutil.rmtree(self.TMP_REPLAYS_DIR)
        shutil.copytree(resume_folder + 'replays-run', self.TMP_REPLAYS_DIR)
        
        jobs = []
        games_restored = 0
        if self.staff_teams_vs_others_only:
            for red_team in self.teams:
                for blue_team in self.staff_teams:
                    if red_team in self.staff_teams: continue #do not play a staff team against another staff team
                    for layout in self.layouts:
                        red_team_name, _ = red_team
                        blue_team_name, _ = blue_team
                        log_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.log'.format(
                            layout=layout, run_id=self.contest_timestamp_id, red_team_name=red_team_name, blue_team_name=blue_team_name)

                        if os.path.isfile(os.path.join(self.TMP_LOGS_DIR, log_file_name)):
                            games_restored += 1
                            #print( "{id} Game {log} restored".format(id=games_restored, log=log_file_name) )
                            jobs.append(self._generate_empty_job(red_team, blue_team, layout))
                        else:
                            print( "{id} Game {log} MISSING".format(id=games_restored, log=log_file_name) )
                            jobs.append(self._generate_job(red_team, blue_team, layout))   
            
        else:

            for red_team, blue_team in combinations(self.teams, r=2):
                for layout in self.layouts:
                    red_team_name, _ = red_team
                    blue_team_name, _ = blue_team
                    log_file_name = '{red_team_name}_vs_{blue_team_name}_{layout}.log'.format(
                        layout=layout, run_id=self.contest_timestamp_id, red_team_name=red_team_name, blue_team_name=blue_team_name)

                    if os.path.isfile(os.path.join(self.TMP_LOGS_DIR, log_file_name)):
                        games_restored += 1
                        print( "{id} Game {log} restored".format(id=games_restored, log=log_file_name) )
                        jobs.append(self._generate_empty_job(red_team, blue_team, layout))
                    else:
                        jobs.append(self._generate_job(red_team, blue_team, layout))   

        #  This is the core package to be transferable to each host
        core_req_file = TransferableFile(local_path=os.path.join(DIR_SCRIPT, self.CORE_CONTEST_TEAM_ZIP_FILE),
                                         remote_path=os.path.join('/tmp', self.CORE_CONTEST_TEAM_ZIP_FILE))

        # create cluster with hots and jobs and run it by starting it, and then analyze output results
        # results will contain all outputs from every game played
        cm = ClusterManager(hosts, jobs, [core_req_file])
        # sys.exit(0)
        results = cm.start()

        print('========================= GAMES FINISHED - NEXT ANALYSING OUTPUT OF GAMES ========================= ')
        self._analyse_all_outputs(results)
        self._calculate_team_stats()


    def _calculate_team_stats(self):
        """
        Compute ladder and create html with results. The html is saved in results_<contest_timestamp_id>/results.html.
        """
        for team, scores in self.ladder.items():
            wins = 0
            draws = 0
            loses = 0
            sum_score = 0
            for s in scores:
                if s == self.ERROR_SCORE:
                    continue
                if s > 0:
                    wins += 1
                elif s == 0:
                    draws += 1
                else:
                    loses += 1
                sum_score += s

            self.team_stats[team] = [((wins * 3) + draws), wins, draws, loses, self.errors[team], sum_score]

    @staticmethod
    def _load_teams(team_names_file):
        team_names = {}
        with open(team_names_file, 'r') as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

            student_id_col = None
            team_col = None
            for row in reader:
                if student_id_col is None:
                    student_id_col = row.index('STUDENT_ID')
                    team_col = row.index('TEAM_NAME')

                student_id = row[student_id_col]

                # couple of controls
                team_name = row[team_col].replace('/', 'NOT_FUNNY').replace(' ', '_')
                if team_name == 'staff_team':
                    logging.warning('staff_team is a reserved team name. Skipping.')
                    continue

                if not student_id or not team_name:
                    continue
                team_names[student_id] = team_name
        return team_names



if __name__ == '__main__':
    settings = load_settings()

    # from getpass import getuser

    # prompt for password (for password authentication or if private key is password protected)
    # hosts = [Host(no_cpu=2, hostname='localhost', username=getuser(), password=getpass(), key_filename=None)]
    # use this if no pass is necessary (for private key authentication)
    # hosts = [Host(no_cpu=2, hostname='localhost', username=getuser(), password=None, key_filename=None)]

    with open(settings['workers_file'], 'r') as f:
        workers_details = json.load(f)['workers']
        logging.info("Host workers details to be used: {}".format(workers_details))

    hosts = [Host(no_cpu=w['no_cpu'], hostname=w['hostname'], username=w['username'], password=w['password'],
                  key_filename=w['private_key_file'], key_password=w['private_key_password']) for w in workers_details]
    del settings['workers_file']

    
    resume_competition_folder = settings['resume_competition_folder']
    del settings['resume_competition_folder']
    
    logging.info("Will create contest runner with options: {}".format(settings))
    runner = ContestRunner(**settings)  # Setup ContestRunner    
    
    if resume_competition_folder != '':
        runner.resume_contest_remotely(hosts, resume_competition_folder)  # Now run ContestRunner with the hosts!
    else:
        runner.run_contest_remotely(hosts) 

    stats_file_url, replays_file_url, logs_file_url = runner.store_results()
    html_generator = HtmlGenerator(settings['www_dir'], settings['organizer'])
    html_generator.add_run(runner.contest_timestamp_id, stats_file_url, replays_file_url, logs_file_url)
    logging.info("Web pages generated. Now cleaning up and closing... Thank you!")

    runner.clean_up()
