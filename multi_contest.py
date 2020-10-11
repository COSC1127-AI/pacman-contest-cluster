import copy
import shutil
import zipfile
import random
import iso8601
import csv
import datetime
import json
import logging

from string import ascii_lowercase

from config import *
from contest_runner import ContestRunner


def list_partition(list_in, n):
    # partitions a list into n (nearly) equal lists: https://stackoverflow.com/questions/3352737/how-to-randomly-partition-a-list-into-n-nearly-equal-parts
    random.shuffle(list_in)
    return [list_in[i::n] for i in range(n)]


def get_agent_factory(team_name):
    """returns the agent factory for a given team"""
    return os.path.join(TEAMS_SUBDIR, team_name, AGENT_FACTORY)


class MultiContest:
    def __init__(self, settings):
        self.layouts = set()
        self.split = settings["split"]
        self.settings = settings

        if not os.path.exists(os.path.join(DIR_SCRIPT, CONTEST_ZIP_FILE)):
            logging.error(f"Contest zip file {CONTEST_ZIP_FILE} could not be found. Aborting.")
            sys.exit(1)

        if not settings["fixed_layouts_file"]:
            logging.error(f"Layouts file {settings['fixed_layouts_file']} could not be found. Aborting.")
            sys.exit(1)

        # this is a folder with the whole contest folder (with system + teams) in the multi-contest folder
        self.tmp_contest_dir = os.path.join(TMP_DIR, TMP_CONTEST_DIR)


        # Setup Pacman CTF environment by extracting it from a clean zip file
        self._prepare_platform(
            os.path.join(DIR_SCRIPT, CONTEST_ZIP_FILE),
            settings["fixed_layouts_file"],
            self.tmp_contest_dir,
            settings["no_fixed_layouts"],
            settings["no_random_layouts"],
            settings.get("fixed_layout_seeds", []),
            settings.get("random_layout_seeds", []),
        )
        # Report layouts to be played, fixed and random (with seeds)
        self.log_layouts()

        # clear out old contest subdirectories
        for contest_folder in os.listdir(TMP_DIR):
            contest_path = os.path.join(TMP_DIR, contest_folder)
            if (
                os.path.isdir(contest_path)
                and contest_folder.startswith("contest-")
                and contest_folder != "contest-run"
            ):
                shutil.rmtree(contest_path)

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
        self.settings["contest_timestamp_id"] = self.contest_timestamp_id

        ## Dump config file for the whole multi-contest
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
                new_split = list_partition(list(new_teams), self.split)
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
                f"Too many fixed seeds layouts selected ({len(fixed_layout_seeds)}) for a total of {no_fixed_layouts} fixed layouts requested to play.")
            exit(1)
        if not fixed_layout_seeds.issubset(
            layouts_available
        ):  # NOT empty, list of layouts provided
            logging.error(f"There are fixed layout seeds that are not available: {fixed_layout_seeds.difference(layouts_available)}.")
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
                f"Too many random seeds layouts ({len(random_seeds)}) for a total of {no_random_layouts} random layouts requested to play.")
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
