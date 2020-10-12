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
    # submissions file format: s???????[_datetime].zip
    # submissions folder format: s???????[_datetime]
    # datetime in ISO8601 format:  https://en.wikipedia.org/wiki/ISO_8601
    def __init__(self, settings):

        self.organizer = settings["organizer"]
        self.max_steps = settings["max_steps"]

        self.www_dir = settings["www_dir"]
        self.stats_archive_dir = os.path.join(
            self.www_dir,
            settings.get("stats_archive_dir", None) or DEFAULT_STATS_ARCHIVE_DIR,
        )
        self.logs_archive_dir = os.path.join(
            self.www_dir,
            settings.get("logs_archive_dir", None) or DEFAULT_LOGS_ARCHIVE_DIR,
        )
        self.replays_archive_dir = os.path.join(
            self.www_dir,
            settings.get("replays_archive_dir", None) or DEFAULT_REPLAYS_ARCHIVE_DIR,
        )

        self.upload_replays = settings["upload_replays"]
        self.upload_logs = settings["upload_logs"]

        # self.maxTimeTaken = Null

        # flag indicating the contest only will run student teams vs staff teams, instead of a full tournament
        self.staff_teams_vs_others_only = settings["staff_teams_vs_others_only"]

        self.contest_timestamp_id = settings["contest_timestamp_id"]

        # a flag indicating whether to compress the logs
        self.compress_logs = settings["compress_logs"]

        self.teams = settings["teams"] + settings["staff_teams"]
        self.staff_teams = settings["staff_teams"]
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

        self.ladder = {n: [] for n, _ in self.teams}
        self.games = []
        self.errors = {n: 0 for n, _ in self.teams}
        self.team_stats = {n: 0 for n, _ in self.teams}

    def _close(self):
        pass

    def clean_up(self):
        pass
        # shutil.rmtree(self.tmp_dir)

    def _generate_command(self, red_team, blue_team, layout):
        (red_team_name, red_team_agent_factory) = red_team
        (blue_team_name, blue_team_agent_factory) = blue_team
        # TODO: make the -c an option at the meta level to "Catch exceptions and enforce time limits"
        command = 'python3 capture.py -c -r "{red_team_agent_factory}" -b "{blue_team_agent_factory}" -l {layout} -i {steps} -q --record --recordLog --delay 0.0 --fixRandomSeed'.format(
            red_team_agent_factory=red_team_agent_factory,
            blue_team_agent_factory=blue_team_agent_factory,
            layout=layout,
            steps=self.max_steps,
        )
        return command

    def _analyse_output(
        self, red_team, blue_team, layout, exit_code, output, total_secs_taken
    ):
        """
        Analyzes the output of a match and updates self.games accordingly.
        """
        (red_team_name, red_team_agent_factory) = red_team
        (blue_team_name, blue_team_agent_factory) = blue_team

        # dump the log of the game into file for the game: red vs blue in layout
        log_file_name = "{red_team_name}_vs_{blue_team_name}_{layout}.log".format(
            layout=layout,
            run_id=self.contest_timestamp_id,
            red_team_name=red_team_name,
            blue_team_name=blue_team_name,
        )
        # results/results_<run_id>/{red_team_name}_vs_{blue_team_name}_{layout}.log
        if output is not None:
            with open(os.path.join(self.tmp_logs_dir, log_file_name), "w") as f:
                try:
                    print(output.decode("utf-8"), file=f)
                except:
                    print(output, file=f)

        else:
            with open(os.path.join(self.tmp_logs_dir, log_file_name), "r") as f:
                try:
                    output = f.read()
                except:
                    output = ""

        if exit_code == 0:
            pass
            # print(
            #     ' Successful: Log in {output_file}.'.format(output_file=os.path.join(self.tmp_logs_dir, log_file_name)))
        else:
            print(
                "Game Failed: Check log in {output_file}.".format(
                    output_file=log_file_name
                )
            )

        score, winner, loser, bug, totaltime = self._parse_result(
            output, red_team_name, blue_team_name, layout
        )

        if winner is None:
            self.ladder[red_team_name].append(score)
            self.ladder[blue_team_name].append(score)
        else:
            self.ladder[winner].append(score)
            self.ladder[loser].append(-score)

        # Next handle replay file
        replay_file_name = "{red_team_name}_vs_{blue_team_name}_{layout}.replay".format(
            layout=layout,
            run_id=self.contest_timestamp_id,
            red_team_name=red_team_name,
            blue_team_name=blue_team_name,
        )

        replays = glob.glob(os.path.join(self.tmp_contest, "replay*"))
        if replays:
            shutil.move(
                replays[0], os.path.join(self.tmp_replays_dir, replay_file_name)
            )
        if not bug:
            self.games.append(
                (red_team_name, blue_team_name, layout, score, winner, totaltime)
            )
        else:
            self.games.append(
                (red_team_name, blue_team_name, layout, ERROR_SCORE, winner, totaltime)
            )

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
                    score = abs(int(line.split("wins by")[1].split("points")[0]))
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

    @staticmethod
    def upload_file(file_full_path, remote_name=None, remove_local=False):
        file_name = os.path.basename(file_full_path)
        remote_name = remote_name or file_name

        logging.info("Transferring %s to transfer.sh service..." % file_name)
        transfer_cmd = "curl --upload-file %s https://transfer.sh/%s" % (
            file_full_path,
            remote_name,
        )
        try:
            # This will yield a byte, not a str (at least in Python 3)
            transfer_url = subprocess.check_output(transfer_cmd, shell=True)
            if "Could not save metadata" in transfer_url:
                raise ValueError("Transfer.sh returns incorrect url: %s" % transfer_url)
            if remove_local:
                print("rm %s" % file_full_path)
                os.system("rm %s" % file_full_path)
                transfer_url = transfer_url.decode()  # convert to string
            logging.info(
                "File %s transfered successfully to transfer.sh service; URL: %s"
                % (file_name, transfer_url)
            )
        except Exception as e:
            # If transfer failed, use the standard server
            logging.error(
                "Transfer-url failed, using local copy to store games. Exception: %s"
                % str(e)
            )
            raise
            # transfer_url = file_name

        return transfer_url

    def store_results(self):
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

        # Process replays: compress and upload
        replays_archive_name = "replays_%s.tar" % self.contest_timestamp_id
        replays_archive_name += ".gz" if self.compress_logs else ""
        replays_archive_full_path = os.path.join(
            self.replays_archive_dir, replays_archive_name
        )
        with tarfile.open(
            replays_archive_full_path, "w:gz" if self.compress_logs else "w"
        ) as tar:
            tar.add(self.tmp_replays_dir, arcname="/")
        if self.upload_replays:
            try:
                replays_file_url = self.upload_file(
                    replays_archive_full_path, remove_local=False
                )
                data_stats["url_replays"] = replays_file_url.decode()
            except Exception as e:
                replays_file_url = os.path.relpath(
                    replays_archive_full_path, self.www_dir
                )
        else:
            replays_file_url = os.path.relpath(
                replays_archive_full_path, self.www_dir
            )  # stats-archive/stats_xxx.json

        # Process replays: compress and upload
        logs_archive_name = "logs_%s.tar" % self.contest_timestamp_id
        logs_archive_name += ".gz" if self.compress_logs else ""
        logs_archive_full_path = os.path.join(self.logs_archive_dir, logs_archive_name)
        with tarfile.open(
            logs_archive_full_path, "w:gz" if self.compress_logs else "w"
        ) as tar:
            tar.add(self.tmp_logs_dir, arcname="/")
        if self.upload_logs:
            try:
                logs_file_url = self.upload_file(
                    logs_archive_full_path, remove_local=False
                )
                data_stats["url_logs"] = logs_file_url.decode()
            except Exception as e:
                logs_file_url = os.path.relpath(logs_archive_full_path, self.www_dir)
        else:
            logs_file_url = os.path.relpath(logs_archive_full_path, self.www_dir)

        # Store stats in a json file
        stats_file_name = "stats_%s.json" % self.contest_timestamp_id  # stats_xxx.json
        stats_file_full_path = os.path.join(
            self.stats_archive_dir, stats_file_name
        )  # www/stats-archive/stats_xxx.json
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

        game_command = self._generate_command(red_team, blue_team, layout)

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

    def _analyse_all_outputs(self, results):
        logging.info(f"About to analyze game result outputs. Number of result output to analyze: {len(results)}")
        for result in results:
            (
                (red_team, blue_team, layout),
                exit_code,
                output,
                error,
                total_secs_taken,
            ) = result
            if not exit_code == 0:
                print(
                    "Game {} VS {} in {} exited with code {} and here is the output:".format(
                        red_team[0], blue_team[0], layout, exit_code, output
                    )
                )
            self._analyse_output(
                red_team, blue_team, layout, exit_code, None, total_secs_taken
            )

    def run_contest_remotely(self, hosts, resume_folder=None, first=True):
        self.prepare_dirs()

        if resume_folder is not None:
            contest_folder = os.path.split(self.tmp_dir)[1]
            resume_folder = os.path.join(resume_folder, contest_folder)
            shutil.rmtree(self.tmp_logs_dir)
            shutil.copytree(os.path.join(resume_folder, "logs-run"), self.tmp_logs_dir)
            shutil.rmtree(self.tmp_replays_dir)
            shutil.copytree(
                os.path.join(resume_folder, "replays-run"), self.tmp_replays_dir
            )
            jobs = self.resume_contest_jobs()
        else:
            jobs = self.run_contest_jobs()

        #  This is the core package to be transferable to each host
        core_req_file = TransferableFile(
            local_path=os.path.join(TMP_DIR, CORE_CONTEST_TEAM_ZIP_FILE),
            remote_path=os.path.join("/tmp", CORE_CONTEST_TEAM_ZIP_FILE),
        )

        # create cluster with hosts and jobs and run it by starting it, and then analyze output results
        # results will contain all outputs from every game played
        if first:
            cm = ClusterManager(hosts, jobs, [core_req_file])
        else:
            # subsequent contests don't need to transfer the files again
            cm = ClusterManager(hosts, jobs, None)
        # sys.exit(0)
        results = cm.start()

        print(
            "========================= GAMES FINISHED - NEXT ANALYSING OUTPUT OF GAMES ========================= "
        )
        self._analyse_all_outputs(results)
        self._calculate_team_stats()

    def run_contest_jobs(self):
        jobs = []
        if self.staff_teams_vs_others_only:
            for red_team in self.teams:
                for blue_team in self.staff_teams:
                    if red_team in self.staff_teams:
                        continue  # do not play a staff team against another staff team
                    for layout in self.layouts:
                        jobs.append(self._generate_job(red_team, blue_team, layout))
        else:
            for red_team, blue_team in combinations(self.teams, r=2):
                for layout in self.layouts:
                    jobs.append(self._generate_job(red_team, blue_team, layout))
        return jobs

    def resume_contest_jobs(self):
        jobs = []
        games_restored = 0
        if self.staff_teams_vs_others_only:
            for red_team in self.teams:
                for blue_team in self.staff_teams:
                    if red_team in self.staff_teams:
                        continue  # do not play a staff team against another staff team
                    for layout in self.layouts:
                        red_team_name, _ = red_team
                        blue_team_name, _ = blue_team
                        log_file_name = (
                            f"{red_team_name}_vs_{blue_team_name}_{layout}.log"
                        )

                        if os.path.isfile(
                            os.path.join(self.tmp_logs_dir, log_file_name)
                        ):
                            games_restored += 1
                            # print( "{id} Game {log} restored".format(id=games_restored, log=log_file_name) )
                            jobs.append(
                                self._generate_empty_job(red_team, blue_team, layout)
                            )
                        else:
                            print(f"{games_restored} Game {log_file_name} MISSING")
                            jobs.append(self._generate_job(red_team, blue_team, layout))

        else:
            for red_team, blue_team in combinations(self.teams, r=2):
                for layout in self.layouts:
                    red_team_name, _ = red_team
                    blue_team_name, _ = blue_team
                    log_file_name = f"{red_team_name}_vs_{blue_team_name}_{layout}.log"
                    log_file_name2 = f"{blue_team_name}_vs_{red_team_name}_{layout}.log"

                    if os.path.isfile(os.path.join(self.tmp_logs_dir, log_file_name)):
                        games_restored += 1
                        print(f"{games_restored} Game {log_file_name} restored")
                        jobs.append(
                            self._generate_empty_job(red_team, blue_team, layout)
                        )
                    elif os.path.isfile(
                        os.path.join(self.tmp_logs_dir, log_file_name2)
                    ):
                        games_restored += 1
                        print(f"{games_restored} Game {log_file_name} restored")
                        jobs.append(
                            self._generate_empty_job(blue_team, red_team, layout)
                        )
                    else:
                        jobs.append(self._generate_job(red_team, blue_team, layout))
        return jobs

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
                if s == ERROR_SCORE:
                    continue
                if s > 0:
                    wins += 1
                elif s == 0:
                    draws += 1
                else:
                    loses += 1
                sum_score += s

            self.team_stats[team] = [
                ((wins * 3) + draws),
                wins,
                draws,
                loses,
                self.errors[team],
                sum_score,
            ]
