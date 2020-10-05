#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This script runs a all-against-all tournament between teams of agents for the Pacman Capture the Flag
project (http://ai.berkeley.edu/contest.html) developed by John DeNero (denero@cs.berkeley.edu) and
Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.

After running the tournament, the script generates a leaderboard report in HTML for web hosting which includes
logs and replays for each game.
                    
The script was developed for RMIT COSC1125/1127 AI course in Semester 1, 2017 by Sebastian Sardina and PhD
student Marco Tamassia. The script is in turn based on an original script from Nir Lipovetzky for local runs.

It is currently maintained by Sebastian Sardina and Nir Lipovetzky; contact them for any question.
"""
__author__ = "Sebastian Sardina, Marco Tamassia, and Nir Lipovetzky"
__copyright__ = "Copyright 2017-2020"
__license__ = "GPLv3"
__repo__ = "https://github.com/AI4EDUC/pacman-contest-cluster"

import os
import sys
import argparse
import json
import logging
import copy
import shutil
import zipfile
import random
import iso8601
import csv
import datetime

from string import ascii_lowercase

# from dataclasses import dataclass
from cluster_manager import Host
from contest_runner import ContestRunner
from pacman_html_generator import HtmlGenerator
from config import *

# check https://stackoverflow.com/questions/10677721/advantages-of-logging-vs-print-logging-best-practices
# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG, datefmt='%a, %d %b %Y %H:%M:%S')
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%a, %d %b %Y %H:%M:%S",
)


# ----------------------------------------------------------------------------------------------------------------------
# Load settings either from config.json or from the command line


def default(str):
    return str + " [Default: %default]"


def load_settings():

    parser = argparse.ArgumentParser(
        description="Run an Pacman Capture the Flag tournament based on "
        "the project developed by John DeNero (denero@cs.berkeley.edu) and Dan Klein "
        "(klein@cs.berkeley.edu) at UC Berkeley (http://ai.berkeley.edu/contest.html).\n"
        "\n"
        "The script produces JSON files with results and an leaderboard report in HTML. \n"
        "\n"
        "Script was developed for RMIT COSC1125/1127 AI course in 2017 (A/Prof. Sebastian Sardina), "
        "and is based on an original script from Dr. Nir Lipovetzky for UoM COMP90054. "
        "From 2017 both have been further developing this tool. \n"
        "\n"
        "Full documentation at https://github.com/AI4EDUC/pacman-contest-cluster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config-file",
        help="configuration file to use, if any.",
    )
    parser.add_argument(
        "--organizer",
        help="name of contest organizer (default: %(default)s).",
        default="Uni Pacman",
    )
    parser.add_argument("--www-dir", help="www output directory.")
    parser.add_argument("--stats-archive-dir", help="stats archive output directory.")
    parser.add_argument(
        "--replays-archive-dir", help="replays archive output directory."
    )
    parser.add_argument("--logs-archive-dir", help="logs archive output directory.")
    parser.add_argument(
        "--compress-logs",
        help="compress logs in a tar.gz file (otherwise, logs will be archived in a tar file).",
        action="store_true",
    )
    parser.add_argument("--workers-file", help="json file with workers details.")
    parser.add_argument(
        "--teams-root",
        help="directory containing the zip files or directories of the teams. See README for format on names.",
    )
    parser.add_argument(
        "--team-names-file",
        help='the path of the csv that contains (at least) two columns headed "STUDENT_ID" and "TEAM_NAME", used to match'
        " submissions with teams. If passed, files/dirs have to be of a certain format <student no>_TIMESTAMP.zip"
        " If no file is specified, team file/dir will be used as name and all will be included.",
    )
    parser.add_argument(
        "--staff-teams-dir",
        help="if given, include staff teams in the given directory (with name staff_team_xxxx.zip).",
    )
    parser.add_argument(
        "--staff-teams-vs-others-only",
        help="if set to true, it will create only games for each student team vs the staff teams. This is useful to provide fast feedback, as it avoids playing student teams in the same game. ",
        action="store_true",
    )
    parser.add_argument(
        "--max-steps",
        help=f"the limit on the number of steps for each game (default: {DEFAULT_MAX_STEPS}).",
    )
    parser.add_argument(
        "--no-fixed-layouts",
        help=f"number of (random) layouts to use from a given fix set (default: {DEFAULT_FIXED_LAYOUTS}).",
    )
    parser.add_argument(
        "--fixed-layout-seeds",
        help="Name of fixed layouts to be included separated by commas, e.g., contest02cCapture,contest12Capture.",
    )
    parser.add_argument(
        "--fixed-layouts-file",
        help=f"zip file where all fixed layouts are stored (default: {DEFAULT_LAYOUTS_ZIP_FILE}).",
    )
    parser.add_argument(
        "--no-random-layouts",
        help=f"number of random layouts to use (default: {DEFAULT_RANDOM_LAYOUTS}).",
    )
    parser.add_argument(
        "--random-layout-seeds",
        help="random seeds for random layouts to use, separated by commas. Eg. 1,2,3.",
    )
    parser.add_argument(
        "--resume-contest-folder",
        help="directory containing the logs and replays from the last failed competition. Can be found in /tmp folder. "
        "Rename it to use the folder as an argument.",
    )
    parser.add_argument(
        "--allow-non-registered-students",
        help="if passed and --team-names-file is given, students without a team are still allowed to participate",
        action="store_true",
    )
    parser.add_argument(
        "--build-config-file",
        help="name of JSON file to write the current options used",
    )
    parser.add_argument(
        "--upload-replays",
        help="upload replays to https://transfer.sh",
        action="store_true",
    )
    parser.add_argument(
        "--upload-logs",
        help="upload logs to https://transfer.sh",
        action="store_true",
    )
    parser.add_argument(
        "--upload-all",
        help="uploads logs and replays into https://transfer.sh.",
        action="store_true",
    )
    parser.add_argument(
        "--split",
        help="split contest into n leagues (default: 1).",
        default=1,
        type=int,
    )

    # TODO: This can be replaced with settings = vars(parser.parse_args()) to generate settings right away!
    # we would have to also set the types of arguments above, for example integers
    args = parser.parse_args()

    # If no arguments are given, stop
    if len(sys.argv) == 1:
        print("No arguments given. Use -h fo help")
        sys.exit(0)

    # Set the default settings first
    settings_default = {}
    settings_default["no_fixed_layouts"] = DEFAULT_FIXED_LAYOUTS
    settings_default["no_random_layouts"] = DEFAULT_RANDOM_LAYOUTS
    settings_default["max_steps"] = DEFAULT_MAX_STEPS
    settings_default["fixed_layouts_file"] = DEFAULT_LAYOUTS_ZIP_FILE
    settings_default["resume_contest_folder"] = None
    settings_default["include_staff_team"] = False
    settings_default["staff_teams_dir"] = None
    settings_default["staff_teams_vs_others_only"] = False
    settings_default["ignore_file_name_format"] = True
    settings_default["team_names_file"] = None
    settings_default["upload_replays"] = args.upload_replays
    settings_default["upload_logs"] = args.upload_logs
    settings_default[
        "allow_non_registered_students"
    ] = args.allow_non_registered_students
    settings_default["split"] = args.split

    # Then set the settings from config file, if any provided
    settings_json = {}
    settings_cli = {}

    if args.resume_contest_folder is not None:
        settings_cli["resume_contest_folder"] = args.resume_contest_folder
        config_json_file = os.path.join(args.resume_contest_folder, DEFAULT_CONFIG_FILE)
        if os.path.exists(config_json_file):
            with open(config_json_file, "r") as f:
                settings_json = json.load(f)
                logging.debug("Configuration file loaded from resume directory")
        else:
            logging.error(
                f"Configuration file {config_json_file} not available in resume directory."
            )
            sys.exit(1)

    if args.config_file is not None:
        if args.resume_contest_folder is not None:
            logging.warning(
                "Configuration file loaded from resume directory, ignoring specified config file"
            )
        else:
            config_json_file = (
                args.config_file
                if args.config_file is not None
                else DEFAULT_CONFIG_FILE
            )
            if os.path.exists(config_json_file):
                with open(config_json_file, "r") as f:
                    settings_json = json.load(f)
                    logging.debug("Configuration file loaded")
            else:
                logging.error(f"Configuration file {config_json_file} not available.")
                sys.exit(1)

    # Now collect all CLI options, override default and config file
    if args.organizer:
        settings_cli["organizer"] = args.organizer

    if args.www_dir:
        settings_cli["www_dir"] = args.www_dir
    if args.compress_logs:
        settings_cli["compress_logs"] = args.compress_logs
    if args.workers_file:
        settings_cli["workers_file"] = args.workers_file

    if args.staff_teams_dir:
        settings_cli["staff_teams_dir"] = args.staff_teams_dir
        settings_cli["include_staff_team"] = True

    if args.staff_teams_vs_others_only:
        settings_cli["staff_teams_vs_others_only"] = True

    if args.teams_root:
        settings_cli["teams_root"] = args.teams_root
    if args.team_names_file:
        settings_cli["team_names_file"] = args.team_names_file
        settings_cli["ignore_file_name_format"] = False

    if args.stats_archive_dir:
        settings_cli["stats_archive_dir"] = args.stats_archive_dir
    if args.replays_archive_dir:
        settings_cli["replays_archive_dir"] = args.replays_archive_dir
    if args.logs_archive_dir:
        settings_cli["logs_archive_dir"] = args.logs_archive_dir

    if args.no_fixed_layouts:
        settings_cli["no_fixed_layouts"] = int(args.no_fixed_layouts)
    if args.fixed_layout_seeds:
        settings_cli["fixed_layout_seeds"] = [
            x for x in args.fixed_layout_seeds.split(",")
        ]
    if args.no_random_layouts:
        settings_cli["no_random_layouts"] = int(args.no_random_layouts)
    if args.random_layout_seeds:
        settings_cli["random_layout_seeds"] = [
            int(x) for x in args.random_layout_seeds.split(",")
        ]
    if args.max_steps:
        settings_cli["max_steps"] = int(args.max_steps)

    if args.upload_all:
        settings_cli["upload_replays"] = True
        settings_cli["upload_logs"] = True
    else:
        if args.upload_replays:
            settings_cli["upload_replays"] = args.upload_replays
        if args.upload_logs:
            settings_cli["upload_logs"] = args.upload_logs

    if args.allow_non_registered_students:
        settings_cli[
            "allow_non_registered_students"
        ] = args.allow_non_registered_students
    if args.split:
        settings_cli["split"] = args.split

    # Now integrate default, config file, and CLI settings, in that order
    settings = {**settings_default, **settings_json, **settings_cli}

    # Check if some important option is missing, if so abort (not used yet)
    missing_parameters = set({}) - set(settings.keys())
    if missing_parameters:
        logging.error(
            "Missing parameters: %s. Aborting." % list(sorted(missing_parameters))
        )
        parser.print_help()
        sys.exit(1)

    # dump current config files into configuration file if requested to do so
    if args.build_config_file:
        logging.info(f"Dumping current options to file {args.build_config_file}")
        with open(args.build_config_file, "w") as f:
            json.dump(settings, f, sort_keys=True, indent=4, separators=(",", ": "))

    return settings


# ----------------------------------------------------------------------------------------------------------------------


def list_partition(list_in, n):
    # partitions a list into n (nearly) equal lists: https://stackoverflow.com/questions/3352737/how-to-randomly-partition-a-list-into-n-nearly-equal-parts
    random.shuffle(list_in)
    return [list_in[i::n] for i in range(n)]


def get_agent_factory(team_name):
    """returns the agent factory for a given team"""
    return os.path.join(TEAMS_SUBDIR, team_name, AGENT_FACTORY)


# @dataclass
# class ContestSettings:
#     organizer: str
#     teams_root: str
#     staff_teams_vs_others_only: bool
#     include_staff_team: bool
#     staff_teams_dir
#     compress_logs
#     max_steps
#     no_fixed_layouts,
#     fixed_layouts_file
#     no_random_layouts
#     team_names_file
#     allow_non_registered_students
#     ignore_file_name_format
#     www_dir
#     fixed_layout_seeds=[]
#     random_seeds=[]
#     stats_archive_dir=None
#     logs_archive_dir=None
#     replays_archive_dir=None
#     upload_replays=False
#     upload_logs=False
#     split=1


class MultiContest:
    def __init__(self, settings):
        self.layouts = set()
        self.split = settings["split"]
        self.settings = settings

        if not os.path.exists(os.path.join(DIR_SCRIPT, CONTEST_ZIP_FILE)):
            logging.error(
                "Contest zip file %s could not be found. Aborting." % CONTEST_ZIP_FILE
            )
            sys.exit(1)

        if not settings["fixed_layouts_file"]:
            logging.error(
                "Layouts file %s could not be found. Aborting."
                % settings["fixed_layouts_file"]
            )
            sys.exit(1)

        self.tmp_contest_dir = os.path.join(TMP_DIR, TMP_CONTEST_DIR)

        # Setup Pacman CTF environment by extracting it from a clean zip file
        self._prepare_platform(
            os.path.join(DIR_SCRIPT, CONTEST_ZIP_FILE),
            settings["fixed_layouts_file"],
            self.tmp_contest_dir,
            settings["no_fixed_layouts"],
            settings["no_random_layouts"],
            settings["fixed_layout_seeds"],
            settings["random_layout_seeds"],
        )

        # Report layouts to be played, fixed and random (with seeds)
        self.log_layouts()

        # unique id for this execution of the contest; used to label logs
        self.contest_timestamp_id = (
            datetime.datetime.now().astimezone(TIMEZONE).strftime("%Y-%m-%d-%H-%M")
        )

        # Setup all of the TEAMS
        teams_dir = os.path.join(self.tmp_contest_dir, TEAMS_SUBDIR)
        if os.path.exists(teams_dir):
            shutil.rmtree(teams_dir)
        os.makedirs(teams_dir)

        # Get all team name mapping from mapping file, If no file is specified, all zip files in team folder will be taken.
        if settings["team_names_file"] is None:
            self.team_names = None
        else:
            self.team_names = self._load_teams(settings["team_names_file"])

        # setup all team directories under contest/team subdir for contest (copy content in .zip to team dirs)

        self.teams = []
        self.staff_teams = []
        self.submission_times = {}

        for submission_file in os.listdir(settings["teams_root"]):
            submission_path = os.path.join(settings["teams_root"], submission_file)
            if submission_file.endswith(".zip") or os.path.isdir(submission_path):
                self._setup_team(
                    submission_path,
                    teams_dir,
                    settings["ignore_file_name_format"],
                    allow_non_registered_students=settings[
                        "allow_non_registered_students"
                    ],
                )

        # Include staff teams if available (ones with pattern STAFF_TEAM_FILENAME_PATTERN)
        if settings["include_staff_team"]:
            for staff_team_submission_file in os.listdir(settings["staff_teams_dir"]):
                match = re.match(
                    STAFF_TEAM_FILENAME_PATTERN,
                    os.path.basename(staff_team_submission_file),
                )
                if match:
                    submission_path = os.path.join(
                        settings["staff_teams_dir"], staff_team_submission_file
                    )
                    if staff_team_submission_file.endswith(".zip") or os.path.isdir(
                        submission_path
                    ):
                        self._setup_team(submission_path, teams_dir, True, False, True)

        # zip directory for transfer to remote workers; zip goes into temp directory
        shutil.make_archive(
            os.path.join(TMP_DIR, CORE_CONTEST_TEAM_ZIP_FILE[:-4]),
            "zip",
            self.tmp_contest_dir,
        )

    def create_contests(self):
        contests = []
        self.settings["fixed_layout_seeds"] = [
            l for l in self.layouts if not l.startswith("RANDOM")
        ]
        self.settings["random_layout_seeds"] = [
            int(l[6:]) for l in self.layouts if l.startswith("RANDOM")
        ]
        team_split = self.split_teams()
        self.settings["teams"] = team_split

        with open(os.path.join(TMP_DIR, DEFAULT_CONFIG_FILE), "w") as f:
            json.dump(
                self.settings, f, sort_keys=True, indent=4, separators=(",", ": ")
            )

        self.settings["layouts"] = self.layouts
        self.settings["staff_teams"] = [
            (team, get_agent_factory(team)) for team in self.staff_teams
        ]

        for i, teams in enumerate(team_split):
            settings = copy.deepcopy(self.settings)
            settings["teams"] = [(team, get_agent_factory(team)) for team in teams]
            settings["tmp_dir"] = os.path.join(TMP_DIR, "contest-" + ascii_lowercase[i])
            settings["contest_timestamp_id"] = (
                self.contest_timestamp_id + "-" + ascii_lowercase[i]
            )
            contests.append(ContestRunner(settings))

        return contests

    def split_teams(self):
        prior_split = self.settings.get("teams")
        if prior_split is not None:
            current_teams = set(self.teams)
            new_teams = current_teams.difference(
                [team for section in prior_split for team in section]
            )
            if new_teams:
                new_split = list_partition(new_teams, self.split)
                return [old + new for old, new in zip(prior_split, reversed(new_split))]
            else:
                return prior_split

        else:
            return list_partition(self.teams, self.split)

    def _prepare_platform(
        self,
        contest_zip_file_path,
        layouts_zip_file_path,
        destination,
        no_fixed_layouts,
        no_random_layouts,
        fixed_layout_seeds=[],
        random_seeds=[],
    ):
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
        contest_zip_file.extractall(os.path.join(destination, "."))
        layouts_zip_file = zipfile.ZipFile(layouts_zip_file_path)
        layouts_zip_file.extractall(os.path.join(destination, "layouts"))

        # Pick no_fixed_layouts layouts from the given set in the layout zip file
        #   if layout seeds have been given use them
        layouts_available = set(
            [file_in_zip[:-4] for file_in_zip in layouts_zip_file.namelist()]
        )
        fixed_layout_seeds = set(fixed_layout_seeds)
        random_seeds = set(random_seeds)

        if no_fixed_layouts > len(layouts_available):
            logging.error(
                "There are not enough fixed layout (asked for %d layouts, but there are only %d)."
                % (no_fixed_layouts, len(layouts_available))
            )
            exit(1)
        if len(fixed_layout_seeds) > no_fixed_layouts:
            logging.error(
                "Too many fixed seeds layouts selected (%d) for a total of %d fixed layouts requested to play."
                % (len(fixed_layout_seeds), no_fixed_layouts)
            )
            exit(1)
        if not fixed_layout_seeds.issubset(
            layouts_available
        ):  # NOT empty, list of layouts provided
            logging.error(
                "There are fixed layout seeds  that are not available: %s."
                % fixed_layout_seeds.difference(layouts_available)
            )
            exit(1)

        # assign the set of fixed layouts to be used: the seeds given and complete with random picks from available
        self.layouts = fixed_layout_seeds.union(
            random.sample(
                layouts_available.difference(fixed_layout_seeds),
                no_fixed_layouts - len(fixed_layout_seeds),
            )
        )

        # Next, pick the random layouts, and included all the seeds provided if any
        if len(random_seeds) > no_random_layouts:
            logging.error(
                "Too many random seeds layouts selected (%d) for a total of %d random layouts requested to play."
                % (len(fixed_layout_seeds), no_fixed_layouts)
            )
            exit(1)

        # complete the mising random layouts
        self.layouts = self.layouts.union(
            set(["RANDOM%s" % x for x in random_seeds])
        )  # add random seeds given, if any
        while len(self.layouts) < no_random_layouts + no_fixed_layouts:
            self.layouts.add("RANDOM%s" % str(random.randint(1, 9999)))

    def log_layouts(self):
        logging.info("Layouts to be played: %s" % self.layouts)
        random_layouts_selected = set(
            [x for x in self.layouts if re.compile(r"RANDOM[0-9]*").match(x)]
        )
        fixed_layouts_selected = self.layouts.difference(random_layouts_selected)

        seeds_strings = [
            m.group(1)
            for m in (
                re.compile(r"RANDOM([0-9]*)").search(layout)
                for layout in random_layouts_selected
            )
            if m
        ]
        seeds = list(map(lambda x: int(x), seeds_strings))
        logging.info("Seeds for RANDOM layouts to be played: %s" % seeds)
        logging.info(
            "Seeds for FIXED layouts to be played: %s"
            % ",".join(fixed_layouts_selected)
        )

    def _setup_team(
        self,
        submission_path,
        destination,
        ignore_file_name_format=False,
        allow_non_registered_students=False,
        is_staff_team=False,
    ):
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
        # NOTE: this is duplicated in ContestRunner._setup_team. Should be abstracted
        if os.path.isdir(submission_path):
            submission_zip_file = None
        else:
            try:
                submission_zip_file = zipfile.ZipFile(submission_path)
            except zipfile.BadZipfile:
                logging.warning(
                    "Submission is not a valid ZIP file nor a folder: %s. Skipping"
                    % submission_path
                )
                return

        # Get team name from submission: if in self.team_names mapping, then use mapping; otherwise use filename

        match = re.match(SUBMISSION_FILENAME_PATTERN, os.path.basename(submission_path))
        submission_time = None
        if match:
            student_id = match.group(1)

            # first get the team of this submission
            if student_id in self.team_names:
                team_name = self.team_names[student_id]
            elif allow_non_registered_students:
                team_name = student_id
            else:
                logging.warning(
                    'Student not registered: "%s" (file %s). Skipping'
                    % (student_id, submission_path)
                )
                return

            # next get the submission date (encoded in filename)
            try:
                submission_time = iso8601.parse_date(match.group(3)).astimezone(
                    TIMEZONE
                )
            except iso8601.iso8601.ParseError:
                if not ignore_file_name_format:
                    logging.warning(
                        'Team zip file "%s" name has invalid date format. Skipping'
                        % submission_path
                    )
                    return
        else:
            if not ignore_file_name_format:
                logging.warning(
                    'Submission zip file "%s" does not correspond to any team. Skipping'
                    % submission_path
                )
                return
            team_name = os.path.basename(submission_path)
            team_name = team_name[:-4] if team_name.endswith(".zip") else team_name

        # This submission will be temporarily expanded into team_destination_dir
        team_destination_dir = os.path.join(destination, team_name)

        if team_name not in self.submission_times:
            if submission_zip_file is None:
                shutil.copytree(submission_path, team_destination_dir)
            else:
                submission_zip_file.extractall(team_destination_dir)
            if is_staff_team:
                self.staff_teams.append(team_name)
            else:
                self.teams.append(team_name)
            self.submission_times[team_name] = submission_time

        elif (
            submission_time is not None
            and self.submission_times[team_name] < submission_time
        ):
            shutil.rmtree(team_destination_dir)
            if submission_zip_file is None:
                shutil.copy(submission_path, team_destination_dir)
            else:
                submission_zip_file.extractall(team_destination_dir)
            self.submission_times[team_name] = submission_time

    @staticmethod
    def _load_teams(team_names_file):
        team_names = {}
        with open(team_names_file, "r") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')

            student_id_col = None
            team_col = None
            for row in reader:
                if student_id_col is None:
                    student_id_col = row.index("STUDENT_ID")
                    team_col = row.index("TEAM_NAME")

                student_id = row[student_id_col]

                # couple of controls
                team_name = row[team_col].replace("/", "NOT_FUNNY").replace(" ", "_")
                if team_name == "staff_team":
                    logging.warning("staff_team is a reserved team name. Skipping.")
                    continue

                if not student_id or not team_name:
                    continue
                team_names[student_id] = team_name
        return team_names


if __name__ == "__main__":
    settings = load_settings()

    # from getpass import getuser

    # prompt for password (for password authentication or if private key is password protected)
    # hosts = [Host(no_cpu=2, hostname='localhost', username=getuser(), password=getpass(), key_filename=None)]
    # use this if no pass is necessary (for private key authentication)
    # hosts = [Host(no_cpu=2, hostname='localhost', username=getuser(), password=None, key_filename=None)]

    with open(settings["workers_file"], "r") as f:
        workers_details = json.load(f)["workers"]
        logging.info("Host workers details to be used: {}".format(workers_details))

    hosts = [
        Host(
            no_cpu=w["no_cpu"],
            hostname=w["hostname"],
            username=w["username"],
            password=w["password"],
            key_filename=w["private_key_file"],
            key_password=w["private_key_password"],
        )
        for w in workers_details
    ]
    # del settings["workers_file"]

    resume_contest_folder = settings["resume_contest_folder"]
    del settings["resume_contest_folder"]

    logging.info("Will create contest runner with options: {}".format(settings))

    multi_contest = MultiContest(settings)
    for runner in multi_contest.create_contests():
        runner.run_contest_remotely(hosts, resume_contest_folder)

        stats_file_url, replays_file_url, logs_file_url = runner.store_results()
        html_generator = HtmlGenerator(settings["www_dir"], settings["organizer"])
        html_generator.add_run(
            runner.contest_timestamp_id, stats_file_url, replays_file_url, logs_file_url
        )
        logging.info("Web pages generated. Now cleaning up and closing... Thank you!")

        runner.clean_up()
