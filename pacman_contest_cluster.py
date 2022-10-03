#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This script runs a all-against-all tournament between teams of agents for the Pacman Capture the Flag
project (http://ai.berkeley.edu/contest.html) developed by John DeNero (denero@cs.berkeley.edu) and
Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.

After running the tournament, the script generates a leaderboard report in HTML for web hosting which includes
logs and replays for each game.
                    
The script was first developed for RMIT COSC1125/1127 AI course in Semester 1, 2017 by Sebastian Sardina and PhD student Marco Tamassia. The script was based on an original one from Nir Lipovetzky for local runs.

Since then, it has been significantly extended; and is currently maintained by Sebastian Sardina and Nir Lipovetzky; contact them for any question.
"""
__author__ = "Sebastian Sardina, Nir Lipovetzky, Marco Tamassia and Andrew Chester"
__copyright__ = "Copyright 2017-2022"
__license__ = "Apache-2.0 license"
__repo__ = "https://github.com/COSC1127/pacman-contest-cluster"

import os
import sys
import argparse
import json
import datetime

# from dataclasses import dataclass
from cluster_manager import Host
from multi_contest import MultiContest
from config import *
import copy


import logging
import coloredlogs
LOGGING_FMT="%(asctime)s %(levelname)-5s %(message)s"
LOGGING_DATE="%a, %d %b %Y %H:%M:%S"
LOGGING_LEVEL=logging.INFO

# check https://stackoverflow.com/questions/10677721/advantages-of-logging-vs-print-logging-best-practices
# logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG, datefmt='%a, %d %b %Y %H:%M:%S')
logging.basicConfig(
    format=LOGGING_FMT,
    level=logging.INFO,
    datefmt=LOGGING_DATE,
)
# Set format and level of debug
coloredlogs.install(level=LOGGING_LEVEL, fmt=LOGGING_FMT, datefmt=LOGGING_DATE)


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

    parser.add_argument("--config-file",
                        help="configuration file to use, if any.")
    parser.add_argument("--organizer",
                        help=f"name of contest organizer (default: {DEFAULT_ORGANIZER}).")
    parser.add_argument("--www-dir",
                        help="www output directory.")
    parser.add_argument("--workers-file",
                        help="json file with workers details.")
    parser.add_argument("--teams-roots",
                        nargs='+',
                        help="directory containing the zip files or directories of the teams. See README for format on names.")
    parser.add_argument("--staff-teams-roots",
                        nargs='+',
                        help="if given, include staff teams in the given directory (with name staff_team_xxxx.zip).")
    parser.add_argument("--staff-teams-vs-others-only",
                        help="if set to true, it will create only games for each student team vs the staff teams. ",
                        action="store_true")
    parser.add_argument("--max-steps",
                        help=f"the limit on the number of steps for each game (default: {DEFAULT_MAX_STEPS}).",
                        type=int)
    parser.add_argument("--fixed-layouts-file",
                        help=f"zip file where all fixed layouts are stored (default: {DEFAULT_LAYOUTS_ZIP_FILE}).")
    parser.add_argument("--no-fixed-layouts",
                        help=f"number of (random) layouts to use from a given fix set (default: {DEFAULT_FIXED_LAYOUTS}).",
                        type=int)
    parser.add_argument("--no-random-layouts",
                        help=f"number of random layouts to use (default: {DEFAULT_RANDOM_LAYOUTS}).",
                        type=int)
    parser.add_argument("--fixed-layout-seeds",
                        nargs='+',
                        help="Fixed layouts to be included separated by spaces, "
                             "e.g., contest02cCapture contest12Capture contest10Capture.")
    parser.add_argument("--random-layout-seeds",
                        nargs='+',
                        help="random seeds for random layouts to use, separated by spaces. Eg. 221 442 3.")
    parser.add_argument("--resume-contest-folder",
                        help="directory containing the logs and replays from the last failed competition. "
                             "Can be found in /tmp folder. Rename it to use the folder as an argument.")
    parser.add_argument("--build-config-file",
                        help="name of JSON file to write the current options used")
    parser.add_argument("--upload-replays",
                        help="upload replays to https://transfer.sh",
                        action="store_true")
    parser.add_argument("--upload-logs",
                        help="upload logs to https://transfer.sh",
                        action="store_true")
    parser.add_argument("--upload-all",
                        help="uploads logs and replays into https://transfer.sh.",
                        action="store_true")
    parser.add_argument("--split",
                        help=f"split contest into n leagues (default: {DEFAULT_NO_SPLIT}).",
                        type=int)
    parser.add_argument("--hide-staff-teams",
                        help="if set to true, it will hide the staff teams from the final leaderboard table. ",
                        action="store_true")
    parser.add_argument("--score-thresholds",
                        nargs='+',
                        type=int,
                        help="Score thresholds to be highlighted in final leaderboard table, "
                             "e.g., 5 8 10 20 50")
    args = vars(parser.parse_args())


    # If no arguments are given, stop
    if len(sys.argv) == 1:
        print("No arguments given. Use -h fo help")
        sys.exit(0)

    # Set the default settings first
    settings_default = {}
    settings_default["organizer"] = DEFAULT_ORGANIZER
    settings_default["no_fixed_layouts"] = DEFAULT_FIXED_LAYOUTS
    settings_default["no_random_layouts"] = DEFAULT_RANDOM_LAYOUTS
    settings_default["max_steps"] = DEFAULT_MAX_STEPS
    settings_default["split"] = DEFAULT_NO_SPLIT
    settings_default["fixed_layouts_file"] = DEFAULT_LAYOUTS_ZIP_FILE
    settings_default["resume_contest_folder"] = None
    settings_default["include_staff_team"] = False
    settings_default["staff_teams_dir"] = None
    settings_default["staff_teams_vs_others_only"] = False
    settings_default["ignore_file_name_format"] = True
    settings_default["upload_replays"] = False
    settings_default["upload_logs"] = False
    settings_default["hide_staff_teams"] = False
    settings_default["score_thresholds"] = None

    # Then set the settings from config file, if any provided
    settings_json = {}
    settings_cli = {}

    # Resume an existing contest: 
    if args['resume_contest_folder'] is not None:
        settings_cli["resume_contest_folder"] = args['resume_contest_folder']
        config_json_file = os.path.join(args['resume_contest_folder'], DEFAULT_CONFIG_FILE)
        if os.path.exists(config_json_file):
            with open(config_json_file, "r") as f:
                settings_json = json.load(f)
                logging.debug("Configuration file loaded from resume directory")
        else:
            logging.error(f"Configuration file {config_json_file} not available in resume directory.")
            sys.exit(1)

        if args['split'] and args['split'] != settings_json["split"]:
            logging.error(
                f"Mismatch in split parameter between CLI and resume folder: {args['split']} vs {settings_json['split']}. Aborting."
            )
            sys.exit(1)

    if args['config_file'] is not None:
        if args['resume_contest_folder'] is not None:
            logging.warning("Configuration file loaded from resume directory already, ignoring specified config file")
        else:
            config_json_file = (
                args['config_file']
                if args['config_file'] is not None
                else DEFAULT_CONFIG_FILE
            )
            if os.path.exists(config_json_file):
                with open(config_json_file, "r") as f:
                    settings_json = json.load(f)
                    logging.debug("Configuration file loaded")
            else:
                logging.error(f"Configuration file {config_json_file} not available.")
                sys.exit(1)

    # Now collect all *given* CLI options that are set into a dictionary
    # Discard every item that is None or a False boolean (i..e, discard all unset options)
    settings_cli = dict(filter(lambda item: (item[1] is not None and (not isinstance(item[1], bool) or item[1])), args.items()))

    if args['staff_teams_roots']:
        settings_cli["include_staff_team"] = True
    if args['upload_all']:
        settings_cli["upload_replays"] = True
        settings_cli["upload_logs"] = True


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
    if args['build_config_file']:
        logging.info(f"Dumping current options to file {args['build_config_file']}")
        with open(args['build_config_file'], "w") as f:
            json.dump(settings, f, sort_keys=True, indent=4, separators=(",", ": "))


    return settings


# ----------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    settings = load_settings()

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

    # Build a multi-contest object
    multi_contest = MultiContest(settings)

    if len(multi_contest.teams) == 0:
        print("No teams to play...")
        exit(1)
    elif len(multi_contest.staff_teams) == 0 and settings['staff_teams_vs_others_only']:
        print("Asked to play against staff team only but none available...")
        exit(1)

    transfer_core_packages = True
    start_time = datetime.datetime.now()
    logging.info(f"########## STARTING MULTI-CONTEST AT: {start_time.astimezone(TIMEZONE).strftime('%Y-%m-%d-%H-%M')}")
    for runner in multi_contest.create_contests():
        start_time_contest = datetime.datetime.now()

        logging.info(f"########## STARTING SPLIT CONTEST: {runner.contest_timestamp_id}")
        results, no_successful_job, avg_time, max_time = runner.run_contest_remotely(hosts, resume_contest_folder, transfer_core_packages)
        logging.info(f"########## GAMES IN SPLIT CONTEST COMPLETED: {no_successful_job} jobs done; {avg_time} avg time/game; {max_time} longest game")
        
        logging.info(f"########## NOW ANALYZING OUTPUTS (may take time...): {runner.contest_timestamp_id}")
        runner.analyze_results(results)
        transfer_core_packages = False   # next contests do not need to transfer core packages again; they are in hosts

        # After it has run, we produce all the WWW content
        logging.info(f"########## ANALYZES OF SPLIT CONTEST DONE, now generating its web page: {runner.contest_timestamp_id}")
        stats_file_url, replays_file_url, logs_file_url = runner.generate_www()

        # OLD, not it is done by runner
        # html_generator = HtmlGenerator(settings["www_dir"], settings["organizer"], settings["score_thresholds"])
        # html_generator.add_run(
        #     runner.contest_timestamp_id, stats_file_url, replays_file_url, logs_file_url
        # )
        logging.info(f"########## WEB PAGES GENERATED for the split contest: {runner.contest_timestamp_id}")
        logging.info(f"########## END OF SPLIT CONTEST {runner.contest_timestamp_id} - TIME TAKEN: {datetime.datetime.now() - start_time_contest}")

    end_time = datetime.datetime.now()
    logging.info(f"########## Ending multi-contest at {end_time.astimezone(TIMEZONE).strftime('%Y-%m-%d-%H-%M')} - Duration: {end_time - start_time}")
    logging.info("########## Thank you!")
        
