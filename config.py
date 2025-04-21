import os
import re
import sys
from zoneinfo import ZoneInfo

DIR_SCRIPT = sys.path[0]
DIR_ASSETS = os.path.join(DIR_SCRIPT, "assets")

# !!!! SUPER IMPORTANT !!!!
# Where Python is installed and the pacman virtual environment
PTYHON_WORKERS = "$HOME/opt/virtual-envs/pacman/bin/python"
DEFAULT_ORGANIZER = "Pacman University"
TIMEZONE = ZoneInfo("Australia/Melbourne")


##########################################################
# Generally the ones below do not need to be changed
##########################################################

ERROR_SCORE = 9999

# Output directories (all inside the WWW folder):
#  run_replays/{red_team_name}_vs_{blue_team_name}_{layout}.replay
#  run_logs/{red_team_name}_vs_{blue_team_name}_{layout}.log
#  replays_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .replay files
#  logs_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .log files
#  stats_archive/replays_{contest_timestamp_id}.json
STATS_ARCHIVE_DIR = "stats-archive"
CONFIG_ARCHIVE_DIR = "config-archive"
LOGS_ARCHIVE_DIR = "logs-archive"
REPLAYS_ARCHIVE_DIR = "replays-archive"

TMP_DIR = "tmp"

TMP_CONTEST_DIR = 'contest-run' # where the contest game script is expanded and kept (to have a full copy)
TMP_REPLAYS_DIR = 'replays-run'
TMP_LOGS_DIR = 'logs-run'

# the package that contains the contest game script (is static; changed only for new contest versions)
CONTEST_ZIP_FILE = os.path.join(DIR_ASSETS, "contest.zip")

# dynamic file constructed that puts together: contest file game simulator + all teams 
# this file is transfered once at the start to the worker hosts
CORE_CONTEST_TEAM_ZIP_FILE = "contest_and_teams.zip"

# STAFF_TEAM_FILENAME_PATTERN = re.compile(r"^staff\_team\_.+\.zip$")
STAFF_TEAM_FILENAME_PATTERN = re.compile(r"^staff\_team\_.+$")
SUBMISSION_FILENAME_PATTERN = re.compile(r"^(s\d+)(_([-+0-9T:.]+))?(\.zip)?$")
TEAMS_SUBDIR = "teams"
AGENT_FILE_NAME = "myTeam.py"

DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_MAX_STEPS = 1200
DEFAULT_FIXED_LAYOUTS = 3
DEFAULT_LAYOUTS_ZIP_FILE = os.path.join(DIR_ASSETS, "layouts.zip")
DEFAULT_RANDOM_LAYOUTS = 3

DEFAULT_NO_SPLIT = 1

LOG_HEADER_MARK = "##########"
