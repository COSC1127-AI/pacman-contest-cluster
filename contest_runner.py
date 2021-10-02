import os
import sys
import re
import shutil
import zipfile
import glob
import tarfile
import subprocess
import json
from itertools import combinations
import logging
from config import *

from cluster_manager import ClusterManager, Job, Host, TransferableFile


class ContestRunner:
    """Class representing one Capture the Flag contest with a set of teams in a set of layouts

    The class creates individual jobs, one per game between teams in the contest, to run each game. 
    It uses ClusterManager to run those jobs in a set of hosts, and then analyses the outputs.

    The main API interface is run_contest_remotely(.) to run one single contest with a set of teams in a set of hosts

    Function _get_game_command() generates the actual command that runs each game:

        python3 capture.py -c -q --record --recordLog --delay 0.0 --fixRandomSeed' -r "{red_team}" -b "{blue_team}" -l {layout} -i {steps}

    """
    def __init__(self, settings):

        self.organizer = settings["organizer"]
        self.max_steps = settings["max_steps"]

        self.www_dir = settings["www_dir"]
        self.stats_archive_dir = os.path.join(
            self.www_dir, STATS_ARCHIVE_DIR,
        )
        self.logs_archive_dir = os.path.join(
            self.www_dir, LOGS_ARCHIVE_DIR,
        )
        self.replays_archive_dir = os.path.join(
            self.www_dir, REPLAYS_ARCHIVE_DIR,
        )

        self.upload_replays = settings["upload_replays"]
        self.upload_logs = settings["upload_logs"]

        # self.maxTimeTaken = Null

        # flag indicating the contest only will run student teams vs staff teams, instead of a full tournament
        self.staff_teams_vs_others_only = settings["staff_teams_vs_others_only"]

        self.contest_timestamp_id = settings["contest_timestamp_id"]

        # a flag indicating whether to hide staff teams in the output
        self.hide_staff_teams = settings["hide_staff_teams"]

        self.teams = settings["teams"]
        self.staff_teams = settings["staff_teams"]
        self.all_teams = self.teams + self.staff_teams
        self.layouts = settings["layouts"]

        self.tmp_dir = settings["tmp_dir"]
        self.tmp_contest = os.path.join(self.tmp_dir, TMP_CONTEST_DIR)
        self.tmp_replays_dir = os.path.join(self.tmp_dir, TMP_REPLAYS_DIR)
        self.tmp_logs_dir = os.path.join(self.tmp_dir, TMP_LOGS_DIR)

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        os.makedirs(self.tmp_dir)

        if os.path.exists(self.tmp_replays_dir):
            shutil.rmtree(self.tmp_replays_dir)
        os.makedirs(self.tmp_replays_dir)

        if os.path.exists(self.tmp_logs_dir):
            shutil.rmtree(self.tmp_logs_dir)
        os.makedirs(self.tmp_logs_dir)

        self.ladder = {n: [] for n, _ in self.all_teams}
        self.games = []
        self.errors = {n: 0 for n, _ in self.all_teams}
        self.team_stats = {n: 0 for n, _ in self.all_teams}


    def _generate_job(self, red_team, blue_team, layout):
        """
        Generates a job command to play red_team against blue team in a layout. This job is run inside the sandbox
        folder for this particular game (e.g., /tmp/cluster_instance_xxxx)

        :param red_team: the path to the red team (e.g., teams/targethdplus/myTeam.py)
        :param blue_team: the path to the blue team (e.g., teams/targethdplus/myTeam.py)
        :param layout: the name of the layout (e.g., RANDOM2737)
        :return: a Job() object with the job to be scheduled in cluster
        """
        red_team_name, _ = red_team
        blue_team_name, _ = blue_team

        game_command = self._get_game_command(red_team, blue_team, layout)

        deflate_command = "mkdir -p {contest_dir} ; unzip -o {zip_file} -d {contest_dir} ; chmod +x -R *".format(
            zip_file=os.path.join("/tmp", CORE_CONTEST_TEAM_ZIP_FILE),
            contest_dir=self.tmp_dir,
        )

        command = "{deflate_command} ; cd {contest_dir} ; {game_command} ; touch {replay_filename}".format(
            deflate_command=deflate_command,
            contest_dir=self.tmp_dir,
            game_command=game_command,
            replay_filename="replay-0",
        )

        replay_file_name = "{red_team_name}_vs_{blue_team_name}_{layout}.replay".format(
            layout=layout,
            run_id=self.contest_timestamp_id,
            red_team_name=red_team_name,
            blue_team_name=blue_team_name,
        )

        log_file_name = "{red_team_name}_vs_{blue_team_name}_{layout}.log".format(
            layout=layout,
            run_id=self.contest_timestamp_id,
            red_team_name=red_team_name,
            blue_team_name=blue_team_name,
        )

        ret_file_replay = TransferableFile(
            local_path=os.path.join(self.tmp_replays_dir, replay_file_name),
            remote_path=os.path.join(self.tmp_dir, "replay-0"),
        )
        ret_file_log = TransferableFile(
            local_path=os.path.join(self.tmp_logs_dir, log_file_name),
            remote_path=os.path.join(self.tmp_dir, "log-0"),
        )

        return Job(
            command=command,
            required_files=[],
            return_files=[ret_file_replay, ret_file_log],
            data=(red_team, blue_team, layout),
            id="{}-vs-{}-in-{}".format(red_team_name, blue_team_name, layout),
        )

    # Generates a job to restore a game read_team vs blue_team in layout
    def _generate_empty_job(self, red_team, blue_team, layout):
        red_team_name, _ = red_team
        blue_team_name, _ = blue_team

        command = ""

        return Job(
            command=command,
            required_files=[],
            return_files=[],
            data=(red_team, blue_team, layout),
            id="{}-vs-{}-in-{}".format(red_team_name, blue_team_name, layout),
        )


    def _get_game_command(self, red_team, blue_team, layout):
        """Generate the shell command to run one game between two teams in a layout

        Args:
            red_team (tuple): red team name and path to file
            blue_team (tuple): blue team name and path to file
            layout (str): layout to be played

        Returns:
            str: shell command to execute using Python and capture.py simulator
        """

        (red_team_name, red_team_path_file) = red_team
        (blue_team_name, blue_team_path_file) = blue_team

        cmd = f'python3 capture.py -c -q --record --recordLog --delay 0.0 --fixRandomSeed'
        cmd = cmd + " " + f'-r "{red_team_path_file}" -b "{blue_team_path_file}" -l {layout} -i {self.max_steps}'

        return cmd

    def _analyse_all_outputs(self, games_results):
        logging.info(
            f"About to analyze game result outputs. Number of result output to analyze: {len(games_results)}")
        for result in games_results:
            (red_team, blue_team, layout), exit_code, output, error, time_taken = result
            if exit_code != 0:
                print(f"Game {red_team[0]} vs {blue_team[0]} in {layout} exited with error code {exit_code}")
            self._analyse_game_output(
                red_team, blue_team, layout, exit_code, time_taken
            )

    def _analyse_game_output(self, red_team, blue_team, layout, exit_code, total_secs_taken):
        """
        Analyzes the output of a match from the log file and adds the following tuple to self.games:
        
            (read_team, blue_team, layout, score, winner, time)
        """
        red_team_name, _ = red_team
        blue_team_name, _ = blue_team

        # dump the log of the game into file for the game: red vs blue in layout
        log_file_name = f"{red_team_name}_vs_{blue_team_name}_{layout}.log"

        # read log text from log file
        with open(os.path.join(self.tmp_logs_dir, log_file_name), "r") as f:
            try:
                log_output = f.read()
            except:
                logging.error(f"Unable to read log file {log_file_name}")
                log_output = ""

        # now parse the output to get all the info: winner, etc
        score, winner, loser, bug, totaltime = self._parse_result(
            log_output, red_team_name, blue_team_name, layout
        )

        if winner is None:
            self.ladder[red_team_name].append(score)
            self.ladder[blue_team_name].append(score)
        else:
            self.ladder[winner].append(score)
            self.ladder[loser].append(-score)

        if bug:
            score = ERROR_SCORE
        
        # Append match game outcome to self.games
        self.games.append((red_team_name, blue_team_name, layout, score, winner, totaltime))

    def _parse_result(self, output, red_team_name, blue_team_name, layout):
        """
        Parses the result log of a match to extract outcome.

        :param output: an iterator of the lines of the result log
        :param red_team_name: name of Red team
        :param blue_team_name: name of Blue team
        :return: a tuple containing score, winner, loser and a flag signaling whether there was a bug
        """
        score = 0
        winner = None
        loser = None
        bug = False
        tied = False
        totaltime = 0

        try:
            output = output.decode()  # convert byte into string
        except:
            pass  # it is already a string

        if output.find("Traceback") != -1 or output.find("agent crashed") != -1:
            bug = True
            # if both teams fail to load, no one wins
            if (
                output.find("Red team failed to load!") != -1
                and output.find("Blue team failed to load!") != -1
            ):
                self.errors[red_team_name] += 1
                self.errors[blue_team_name] += 1
                winner = None
                loser = None
                score = ERROR_SCORE
            elif (
                output.find("Red agent crashed") != -1
                or output.find("redAgents = loadAgents") != -1
                or output.find("Red team failed to load!") != -1
            ):
                self.errors[red_team_name] += 1
                winner = blue_team_name
                loser = red_team_name
                score = 1
            elif (
                output.find("Blue agent crashed") != -1
                or output.find("blueAgents = loadAgents") != -1
                or output.find("Blue team failed to load!")
            ):
                self.errors[blue_team_name] += 1
                winner = red_team_name
                loser = blue_team_name
                score = 1
            else:
                logging.error(
                    "Note able to parse out for game {} vs {} in {} (traceback available, but couldn't get winner!)".format(
                        red_team_name, blue_team_name, layout
                    )
                )
        else:
            for line in output.splitlines():
                if line.find("wins by") != -1:
                    score = abs(
                        int(line.split("wins by")[1].split("points")[0]))
                    if line.find("Red") != -1:
                        winner = red_team_name
                        loser = blue_team_name
                    elif line.find("Blue") != -1:
                        winner = blue_team_name
                        loser = red_team_name
                if line.find("The Blue team has returned at least ") != -1:
                    score = abs(
                        int(
                            line.split("The Blue team has returned at least ")[1].split(
                                " "
                            )[0]
                        )
                    )
                    winner = blue_team_name
                    loser = red_team_name
                elif line.find("The Red team has returned at least ") != -1:
                    score = abs(
                        int(
                            line.split("The Red team has returned at least ")[1].split(
                                " "
                            )[0]
                        )
                    )
                    winner = red_team_name
                    loser = blue_team_name
                elif line.find("Tie Game") != -1 or line.find("Tie game") != -1:
                    winner = None
                    loser = None
                    tied = True

                if line.find("Total Time Game: ") != -1:
                    totaltime = int(
                        float(line.split("Total Time Game: ")[1].split(" ")[0])
                    )

            # signal strange case where script was unable to find outcome of game - should never happen!
            if winner is None and loser is None and not tied:
                logging.error(
                    "Note able to parse out for game {} vs {} in {} (no traceback available)".format(
                        red_team_name, blue_team_name, layout
                    )
                )
                print(output)
                winner = None
                loser = None
                tied = True
                score = -1
                # sys.exit(1)

        return score, winner, loser, bug, totaltime

    def _calculate_team_stats(self):
        """
        From each individual game, compute stats per team (% won, points, wins, etc.) and store it in self.team_stats
        """
        staff_team_names = [t[0] for t in self.staff_teams]
        for team, scores in self.ladder.items():
            if self.hide_staff_teams and team in staff_team_names:
                # remove staff team from dictionary.
                self.team_stats.pop(team, None)
                continue
            wins = 0
            draws = 0
            loses = 0
            sum_score = 0
            for s in scores:
                if s == ERROR_SCORE:
                    continue
                if s > 0:
                    wins += 1
                elif s == 0:
                    draws += 1
                else:
                    loses += 1
                sum_score += s

            points = (wins * 3) + draws
            self.team_stats[team] = [
                ((points*100)/(3*(wins+draws+loses))) if wins+draws+loses > 0 else 0,
                points,
                wins,
                draws,
                loses,
                self.errors[team],
                sum_score,
            ]


    ########################################################################
    # NOW THE API FOR THE CLASS
    ########################################################################

    @staticmethod
    def upload_file(file_full_path, remote_name=None, remove_local=False):
        """Transfers a file to service transfer.sh

        Args:
            file_full_path (str): file to be transferred
            remote_name (str, optional): file name at remote (if different). Defaults to None.
            remove_local (bool, optional): local has to be deleted. Defaults to False.

        Raises:
            ValueError: error when transferring the file to remote service

        Returns:
            [str]: URL link to remote for the file
        """
        file_name = os.path.basename(file_full_path)
        remote_name = remote_name or file_name

        logging.info(f"Transferring {file_name} to transfer.sh service...")

        transfer_cmd = f"curl --upload-file {file_full_path} https://transfer.sh/{remote_name}"
        try:
            # This will yield a byte, not a str (at least in Python 3)
            transfer_url = subprocess.check_output(transfer_cmd, shell=True)
            if "Could not save metadata" in transfer_url:
                raise ValueError(
                    f"Transfer.sh returns incorrect url: {transfer_url}")
            if remove_local:
                print("rm %s" % file_full_path)
                os.system("rm %s" % file_full_path)
                transfer_url = transfer_url.decode()  # convert to string
            logging.info(
                f"File {file_name} transfered successfully to transfer.sh service; URL: {transfer_url}"
            )
        except Exception as e:
            # If transfer failed, use the standard server
            logging.error(
                f"Transfer-url failed, using local copy to store games. Exception: {e}"
            )
            raise
            # transfer_url = file_name

        return transfer_url

    def store_results(self):
        """Generates all the resulting files for the contest: log, replays, stat packs under the WWW output dir

        This will compress all the logs and replays and stats into single files and per team (for dashboard)

        Returns:
            [tuple]: the URL or path to the stats, replays, and logs
        """

        # Basic data stats
        data_stats = {
            "games": self.games,
            "team_stats": self.team_stats,
            "random_layouts": [l for l in self.layouts if l.startswith("RANDOM")],
            "fixed_layouts": [l for l in self.layouts if not l.startswith("RANDOM")],
            "max_steps": self.max_steps,
            "organizer": self.organizer,
            "timestamp_id": self.contest_timestamp_id,
        }

        # PROCESS REPLAYS: compress (and pssibly upload)
        replays_archive_name = f"replays_{self.contest_timestamp_id}.tar.gz"
        replays_archive_full_path = os.path.join(
            self.replays_archive_dir, replays_archive_name
        )
        with tarfile.open(
            replays_archive_full_path, "w:gz") as tar:
            tar.add(self.tmp_replays_dir, arcname="/")
        if self.upload_replays:
            try:
                replays_file_path = self.upload_file(
                    replays_archive_full_path, remove_local=False
                )
                data_stats["url_replays"] = replays_file_path.decode()
            except Exception as e:
                replays_file_path = os.path.relpath(
                    replays_archive_full_path, self.www_dir
                )
        else:
            replays_file_path = os.path.relpath(
                replays_archive_full_path, self.www_dir
            )  # stats-archive/stats_xxx.json

        # Copy folder
        replays_folder_name = f'replays_{self.contest_timestamp_id}'
        replays_archive_full_path = os.path.join(
            self.replays_archive_dir, replays_folder_name)
        shutil.copytree(self.tmp_replays_dir, replays_archive_full_path)

        # Create replay compress archives for each team
        # store the files without the folders
        for t in self.team_stats.keys():
            replays_folder_name = f'replays_{self.contest_timestamp_id}'
            replays_archive_name = f'replays_{t}.tar.gz'
            replays_archive_full_path =os.path.abspath(os.path.join(
                self.replays_archive_dir, replays_folder_name, replays_archive_name))
            replays_folder_full_path = os.path.abspath(os.path.join(
                self.replays_archive_dir, replays_folder_name))
            replay_files_to_pack = ' '.join([os.path.basename(f) for f in glob.glob(f"{replays_folder_full_path}/*{t}*")])
            os.system(
                f'tar zcf {replays_archive_full_path} -C {replays_folder_full_path} {replay_files_to_pack}')

        # PROCESS LOGS: compress (and possibly upload)
        logs_archive_name = f"logs_{self.contest_timestamp_id}.tar.gz"
        logs_archive_full_path = os.path.join(
            self.logs_archive_dir, logs_archive_name)
        with tarfile.open(
            logs_archive_full_path, "w:gz") as tar:
            tar.add(self.tmp_logs_dir, arcname="/")
        if self.upload_logs:
            try:
                logs_file_path = self.upload_file(
                    logs_archive_full_path, remove_local=False
                )
                data_stats["url_logs"] = logs_file_path.decode()
            except Exception as e:
                logs_file_path = os.path.relpath(
                    logs_archive_full_path, self.www_dir)
        else:
            logs_file_path = os.path.relpath(
                logs_archive_full_path, self.www_dir)

        # Copy folder
        logs_folder_name = f'logs_{self.contest_timestamp_id}'
        logs_archive_full_path = os.path.join(
            self.logs_archive_dir, logs_folder_name)
        shutil.copytree(self.tmp_logs_dir, logs_archive_full_path)

        # Create tar.gz log archives for each team
        # store the files without the folders
        for t in self.team_stats.keys():
            logs_folder_name = f'logs_{self.contest_timestamp_id}'
            logs_archive_name = f'logs_{t}.tar.gz'
            logs_archive_full_path = os.path.join(
                self.logs_archive_dir, logs_folder_name, logs_archive_name)
            logs_folder_full_path = os.path.join(
                self.logs_archive_dir, logs_folder_name)

            log_files_to_pack = ' '.join([os.path.basename(f) for f in glob.glob(f"{logs_folder_full_path}/*{t}*")])
            os.system(
                f'tar zcf {logs_archive_full_path} -C {logs_folder_full_path} {log_files_to_pack}')

        # STORE STATS in a json file
        # stats_xxx.json
        stats_file_name = f"stats_{self.contest_timestamp_id}.json"
        # www/stats-archive/stats_xxx.json
        stats_file_full_path = os.path.join(
            self.stats_archive_dir, stats_file_name)
        stats_file_rel_path = os.path.relpath(
            stats_file_full_path, self.www_dir)
        with open(stats_file_full_path, "w") as f:
            json.dump(data_stats, f)

        return stats_file_rel_path, replays_file_path, logs_file_path


    def run_contest_remotely(self, hosts, resume_folder=None, transfer_core=True):
        """This is the MAIN API function to actually run a single contest in a cluster.
        Notice that a Multi-contest is a set of contests.

        1. First, build a (huge) list of Jobs that must be run, one per game.
        2. Creates and runs a ClusterManager with that jobs
        3. Process outputs and build stats

        Can either start a contest from scratch or resume a previous one from a folder.

        Args:
            hosts (list(Host)): list of namedtuple Host to run the contest
            resume_folder (str, optional): folder with temp data of previous contest to resume. Defaults to None.
            transfer_core (bool, optional): True to transfer core files. Defaults to True.
        """

        # prepare local folders to store replays, logs, stats, etc.
        if not os.path.exists(self.stats_archive_dir):
            os.makedirs(self.stats_archive_dir)
        if not os.path.exists(self.replays_archive_dir):
            os.makedirs(self.replays_archive_dir)
        if not os.path.exists(self.logs_archive_dir):
            os.makedirs(self.logs_archive_dir)

        # next calculate all jobs that must be run
        if resume_folder is not None:
            # if we are resuming, copy all logs and replays and then resume
            contest_folder = os.path.split(self.tmp_dir)[1]
            resume_folder = os.path.join(resume_folder, contest_folder)
            shutil.rmtree(self.tmp_logs_dir)
            shutil.copytree(os.path.join(
                resume_folder, "logs-run"), self.tmp_logs_dir)
            shutil.rmtree(self.tmp_replays_dir)
            shutil.copytree(
                os.path.join(
                    resume_folder, "replays-run"), self.tmp_replays_dir
            )
            jobs = self._generate_contest_jobs(resume=True)
        else:
            jobs = self._generate_contest_jobs(resume=False)

        # Create ClusterManager to run jobs in hosts and start it to run all jobs
        # Variable results will contain ALL outputs from every game played, to be analyzed then
        core_req_files = None
        if transfer_core:
            #  This is the core package to be transferable to each host
            core_req_files = [TransferableFile(
                local_path=os.path.join(TMP_DIR, CORE_CONTEST_TEAM_ZIP_FILE),
                remote_path=os.path.join("/tmp", CORE_CONTEST_TEAM_ZIP_FILE),
            )]
        cm = ClusterManager(hosts, jobs, core_req_files)
        results = cm.start()
        logging.info(
            "########## GAMES FINISHED - NEXT ANALYSING OUTPUT OF GAMES")

        # Time to analyze all the outputs
        self._analyse_all_outputs(results)
        self._calculate_team_stats()
        logging.info("########## ANALYSIS OF GAME OUTPUTS COMPLETED")

    def _generate_contest_jobs(self, resume=False):
        """Generate a list of Jobs for the games to play

        Uses _generate_empty_job() and _generate_job() to build an actual Job

        Args:
            resume (bool, optional): True if we are resuming a previous contest and some logs have been copied across already. Defaults to False.

        Returns:
            [list(Jobs)]: list of all jobs to run, each being a game
        """
        jobs = []
        games_restored = 0
        if self.staff_teams_vs_others_only:
            for red_team in self.teams:
                for blue_team in self.staff_teams:
                    for layout in self.layouts:
                        # remember red_team = (name of team, path of file)
                        # when playing staff teams only, team always plays red
                        log_file_name = f"{red_team[0]}_vs_{blue_team[0]}_{layout}.log"
                        if resume and os.path.isfile(os.path.join(self.tmp_logs_dir, log_file_name)):
                            games_restored += 1
                            print(f"{games_restored} Game {log_file_name} restored")
                            jobs.append(self._generate_empty_job(red_team, blue_team, layout))
                            continue
                        
                        # either not resume anything or log file does not exist
                        jobs.append(self._generate_job(red_team, blue_team, layout))
        else:
            for red_team, blue_team in combinations(self.all_teams, r=2):
                for layout in self.layouts:
                    # remember red_team = (name of team, path of file)
                    log_file_name = f"{red_team[0]}_vs_{blue_team[0]}_{layout}.log"
                    if resume and os.path.isfile(os.path.join(self.tmp_logs_dir, log_file_name)):
                        games_restored += 1
                        print(f"{games_restored} Game {log_file_name} restored")
                        jobs.append(self._generate_empty_job(red_team, blue_team, layout))
                        continue
                    log_file_name = f"{blue_team[0]}_vs_{red_team[0]}_{layout}.log"
                    if resume and os.path.isfile(os.path.join(self.tmp_logs_dir, log_file_name)):
                        games_restored += 1
                        print(f"{games_restored} Game {log_file_name} restored")
                        jobs.append(self._generate_empty_job(blue_team, red_team, layout))
                        continue

                    # either not resume anything or log file does not exist
                    jobs.append(self._generate_job(red_team, blue_team, layout))
        if games_restored > 0:
                print(f'A total of {games_restored} games have been restored. Missing: {len(jobs)-games_restored}', flush=True)
        return jobs
