import os
import re
import sys
from pytz import timezone


DIR_SCRIPT = sys.path[0]


ERROR_SCORE = 9999

DEFAULT_ORGANIZER = "Uni Pacman",

# Output directories:
#  run_replays/{red_team_name}_vs_{blue_team_name}_{layout}.replay
#  run_logs/{red_team_name}_vs_{blue_team_name}_{layout}.log
#  replays_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .replay files
#  logs_archive/replays_{contest_timestamp_id}.tar.gz  # lots of .log files
#  stats_archive/replays_{contest_timestamp_id}.json
DEFAULT_STATS_ARCHIVE_DIR = "stats-archive"
DEFAULT_LOGS_ARCHIVE_DIR = "logs-archive"
DEFAULT_REPLAYS_ARCHIVE_DIR = "replays-archive"

TMP_DIR = "tmp"

TMP_CONTEST_DIR = 'contest-run'
TMP_REPLAYS_DIR = 'replays-run'
TMP_LOGS_DIR = 'logs-run'

CONTEST_ZIP_FILE = "contest.zip"
STAFF_TEAM_ZIP_FILE = [
    "staff_team_basic.zip",
    "staff_team_medium.zip",
    "staff_team_top.zip",
]
STAFF_TEAM_FILENAME_PATTERN = re.compile(r"^staff\_team\_.+\.zip$")
TEAMS_SUBDIR = "teams"
RESULTS_DIR = "results"
TIMEZONE = timezone("Australia/Melbourne")
CORE_CONTEST_TEAM_ZIP_FILE = "contest_and_teams.zip"
SUBMISSION_FILENAME_PATTERN = re.compile(r"^(s\d+)(_([-+0-9T:.]+))?(\.zip)?$")
AGENT_FACTORY = "myTeam.py"

DEFAULT_MAX_STEPS = 1200
DEFAULT_FIXED_LAYOUTS = 3
DEFAULT_LAYOUTS_ZIP_FILE = os.path.join(DIR_SCRIPT, "layouts.zip")
DEFAULT_RANDOM_LAYOUTS = 3
DEFAULT_CONFIG_FILE = "config.json"

DEFAULT_NO_SPLIT = 1