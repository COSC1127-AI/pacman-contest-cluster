#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
ClusterManager manages a set of remote workers and distributes a list of jobs using a greedy policy (jobs are assigned,
in order, to the first free worker. Transfers and communications are done over SSH.

The manager creates a temporary environment for each job, and can copy files to and from such environment (via relative
paths) or anywhere else (via absolute paths).

Extreme care is recommended to both commands and file paths passed: this script performs no checks whatsoever - it's on
you!
"""
from collections import namedtuple
from queue import Queue
import random
from time import sleep
import os
import datetime
from joblib import Parallel, delayed
from getpass import getpass, getuser

# doc for paramiko: http://docs.paramiko.org/en/2.4/api/client.html
from paramiko.config import SSHConfig
from paramiko.client import SSHClient
from paramiko.rsakey import RSAKey
from paramiko.proxy import ProxyCommand
from paramiko import AutoAddPolicy

import logging
import traceback

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%a, %d %b %Y %H:%M:%S",
)
logging.getLogger("paramiko").setLevel(logging.WARNING)

# Three namedtuples that will be extensively used to manage remotes
Host = namedtuple(
    "Host",
    ["no_cpu", "hostname", "username", "password", "key_filename", "key_password"]
)
Job = namedtuple(
    "Job", ["command", "required_files", "return_files", "id", "data"]
)
TransferableFile = namedtuple(
    "TransferableFile", ["local_path", "remote_path"]
)

# Keep track of the number of total jobs to run and number of jobs completed (for reporting)
no_total_jobs = 0
no_successful_jobs = 0
no_failed_jobs = 0
time_games = []  # list of seconds, one per game finished
time_start = datetime.datetime.now()

CORE_PACKAGE_DIR = "/tmp/pacman_files"
NO_LOCAL_RETRIES = (
    1  # Number of retries when a remote command failed (e.g., connection lost)
)

class ErrorInGame(Exception):
    """raise this when there's a lookup error for my app"""


class ClusterManager:
    def __init__(self, hosts, jobs, core_req_file=None):
        """Initialize a ClusterManager to run jobs in hosts

        Args:
            hosts (list[Host]): list of hosts in the cluster
            jobs (list[Job]): list of jobs to execute in hosts
            core_req_file (list(str), optional): list of files to transfer to hosts. Defaults to None.
        """
        self.hosts = hosts  
        self.jobs = jobs  
        self.workers = []  # type: 'List[SSHClient]'
        self.pool = Queue()  # type: 'Queue[SSHClient]'
        self.no_tries = NO_LOCAL_RETRIES

        total_no_workers = sum(host.no_cpu for host in hosts)
        # https: // pythonhosted.org / joblib / generated / joblib.Parallel.html

        global no_total_jobs
        global no_failed_jobs
        global no_successful_jobs

        no_total_jobs = len(self.jobs)
        no_successful_jobs = 0
        no_failed_jobs = 0
        logging.info(f"########## ABOUT TO RUN {no_total_jobs} jobs in {len(hosts)} hosts ({total_no_workers} CPUs)")

        # Firsts, authenticate and build all workers (each Hostname + core gives a worker)
        self.workers = Parallel(total_no_workers, backend="threading")(
            delayed(create_worker)(host)
            for host in self.hosts
            for _ in range(host.no_cpu)
        )

        # Second, transfer the required core files to each hostname, if any
        #  (this is good because there there will be many less than workers, just one per IP)
        logging.info("FIRST COPYING REQUIRED FILES TO HOSTS....")
        if core_req_file is not None:
            Parallel(len(self.hosts), backend="threading")(
                delayed(transfer_core_package)(
                    host.hostname, self.workers, core_req_file
                )
                for host in self.hosts
            )

        # Put all workers in pool
        for worker in self.workers:
            self.pool.put(worker)

    def start(self):
        global time_start
        time_start = datetime.datetime.now()
        jobs_list = self.jobs

        results = (
            []
        )  # list of results: job.data, exit_code, result_out, result_err, job_secs_taken
        while jobs_list:
            results_run = Parallel(self.pool.qsize(), backend="threading")(
                delayed(run_job)(self.pool, job) for job in jobs_list
            )

            # Remove all failed games
            while None in results_run:
                results_run.remove(None)

            games_failed = [    
                job_data
                for job_data, exit_code, _, _, _ in results_run
                if exit_code == -1
            ]
            jobs_list = [
                j for j in jobs_list if j.data in games_failed
            ]  # extract failed jobs (to retry)
            good_results = [
                tuple(result) for result in results_run if not result[1] == -1
            ]
            results = (
                results + good_results
            )  # keep non-error results only (rest will be re-tried)

        if len(time_games) > 0:
            avg_secs_game = round(sum(time_games) / len(time_games), 0)
            max_secs_game = round(max(time_games), 0)
        else:
            avg_secs_game = 0
            max_secs_game = 0

        return results, no_successful_jobs, datetime.timedelta(seconds=avg_secs_game), datetime.timedelta(seconds=max_secs_game)


def create_worker(host):
    config = SSHConfig()
    proxy = None
    if os.path.exists(os.path.expanduser("~/.ssh/config")):
        config.parse(open(os.path.expanduser("~/.ssh/config")))
        if host.hostname is not None and "proxycommand" in config.lookup(host.hostname):
            proxy = ProxyCommand(config.lookup(host.hostname)["proxycommand"])

    # proxy = paramiko.ProxyCommand("ssh -o StrictHostKeyChecking=no e62439@131.170.5.132 nc 118.138.239.241 22")

    worker = SSHClient()
    worker.load_system_host_keys()
    worker.set_missing_host_key_policy(AutoAddPolicy())

    worker.hostname = (
        host.hostname
    )  # store all this for later reference (e.g., logging, reconnection)
    worker.username = host.username
    worker.password = host.password
    worker.proxy = proxy
    if not host.key_filename is None:
        worker.pkey = RSAKey.from_private_key_file(host.key_filename, host.key_password)
    else:
        worker.pkey = None

    # time.sleep(4)
    # worker.connect(hostname=host.hostname, username=host.username, password=host.password, key_filename=host.key_filename, sock=proxy, timeout=3600)

    worker.connect(
        hostname=host.hostname,
        username=host.username,
        password=host.password,
        pkey=worker.pkey,
        sock=proxy,
    )

    return worker


# Transfer the core package and leave it in /tmp/pacman_files
def transfer_core_package(hostname, workers, required_files):
    """Transfers a set of required_files to the worker with hostname

    #TODO:  given that the hostname field in workers is already the IP, does it make sense to pass workers, rather than just using hostname

    Args:
        hostname (str): host to transfer the file
        workers (list(dict)): list of workers (one has is hostname)
        required_files (list(TransferableFile)): list of files to transfer
    """
    # Find a worker for this hostname and transfer the required files to des_dir
    for worker in workers:
        if worker.hostname == hostname:
            # do a full clean of previous temporary directory at worker
            worker.exec_command("rm -rf /tmp/cluster_instance*")

            logging.info(f"[START] CORE PACKAGE TRANSFERRED TO HOST {hostname}\n")
            sftp = worker.open_sftp()
            for tf in required_files:
                sftp.put(localpath=tf.local_path, remotepath=tf.remote_path)
            sftp.close()
            logging.info(f"[END] CORE PACKAGE TRANSFERRED TO HOST {hostname}\n")
            break
    return


def run_job(pool, job):
    global no_successful_jobs
    global no_failed_jobs
    global no_total_jobs

    #  worker is a SSHClient
    worker = pool.get()

    # We tried NO_RETRIES time - and then give up....
    for i in range(NO_LOCAL_RETRIES):
        try:
            # time.sleep(randint(1, 10))
            # TODO: does not work when filename has a ' like Sebcant'code
            result_job_on_worker = run_job_on_worker(worker, job)
            no_successful_jobs += 1
        # TODO: this captures any error that may happen when doing the job in the worker. Is it enough?
        except ErrorInGame as e:
            # Somehow some games the zip does do not un-compress correctly.....
            logging.error(
                "Job with ID {} has FAILED (will retry) with exception: {}".format(
                    job.id, str(e)
                )
            )
            if i < NO_LOCAL_RETRIES - 1:  # i is zero indexed
                # sleep(4)
                continue
            else:
                no_failed_jobs += 1
                logging.error(
                    "I am giving up local retying job {} in worker {}, too many local failures...".format(
                        job.id, worker.hostname
                    )
                )
                result_job_on_worker = (
                    job.data,
                    -1,
                    "",
                    "Match did not work: {}".format(str(e)),
                    1,
                )
        except Exception as e:
            logging.error(
                "Somehow the job {} FAILED to execute with exception: {}".format(
                    str(job.id), str(job)
                )
            )
            traceback.print_exc()
            worker.close()
            worker.connect(
                hostname=worker.hostname,
                username=worker.username,
                password=worker.password,
                pkey=worker.pkey,
                sock=worker.proxy,
            )
            if i < NO_LOCAL_RETRIES - 1:  # i is zero indexed
                continue
            else:
                no_failed_jobs += 1
                logging.error("I am giving up on job %s" % str(job.id))
                # result_job_on_worker = job.data, -1, "", "Match did not work", 1
                result_job_on_worker = None
        break
    games_played = no_successful_jobs + no_failed_jobs
    games_left = no_total_jobs - no_successful_jobs
    secs_so_far = (datetime.datetime.now() - time_start).total_seconds()
    est_time_left = round((games_left * secs_so_far) / games_played, 0)
    logging.info(
        "Jobs COMPLETED: (%d successful, %d failed) of %d total games (%d games left; estimated time left: %s)"
        % (
            no_successful_jobs,
            no_failed_jobs,
            no_total_jobs,
            games_left,
            str(datetime.timedelta(seconds=est_time_left)),
        )
    )

    pool.put(worker)
    return result_job_on_worker


def report_progress_bytes_transfered(xfer, to_be_xfer, job_id):
    remains_per = 0.000
    remains_per = (xfer / to_be_xfer) * 100
    logging.debug(f"Complete percent for job {job_id}: {remains_per:.2f}% - ({xfer} bytes transfered out of {to_be_xfer})")


def report_match(job):
    return job.id


def _rmdir(sftp, path):
    files = sftp.listdir(path)

    for f in files:
        filepath = os.path.join(path, f)
        try:
            sftp.remove(filepath)
        except IOError:
            _rmdir(sftp, filepath)

    sftp.rmdir(path)


def run_job_on_worker(worker, job):
    global max_secs_game

    # create remote env
    instance_id = "{}-{}".format(
        job.id.replace(" ", "_"), datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    )
    dest_dir = f"/tmp/cluster_instance_{instance_id}"
    
    logging.info(f"ABOUT TO RUN JOB in host {worker.hostname} ({dest_dir}): {report_match(job)}")
    sftp = worker.open_sftp()
    try:
        sftp.mkdir(dest_dir)
    except IOError as io:  # dir already exists!
        logging.warning(f"IOError while creating dir {dest_dir} in host {worker.hostname}: ", io)
        traceback.print_exc()
        _rmdir(sftp, dest_dir)
        # worker.exec_command('rm -rf %s' % dest_dir)
        sftp.mkdir(dest_dir)
    except Exception as e:  # all other catches
        logging.warning(f"Error creating directory {dest_dir} in host {worker.hostname}: ", e)
        traceback.print_exc()
        _rmdir(sftp, dest_dir)
        sftp.mkdir(dest_dir)

    sftp.chdir(dest_dir)

    # If the job requires files transfer them to the remote path
    # (for pacman now, required files is empty, as we transfer the core package once at the start and then copy it)
    for tf in job.required_files:
        # sftp.put(localpath=tf.local_path, remotepath=tf.remote_path,
        #          callback=lambda x, y: report_progress_bytes_transfered(x, y, str(job.id)))
        sftp.put(localpath=tf.local_path, remotepath=tf.remote_path)

    logging.debug(f"ABOUT TO EXECUTE command in host {worker.hostname} dir {dest_dir}: {job.command}")
    # run job
    startTime = datetime.datetime.now()
    actual_command = f"""cd {dest_dir} ; sh -c '{job.command}'"""
    try:
        # TODO: do we want to put a timeout here in case the call does not return? some pacman games take 3 min eh
        # _, ssh_stdout, ssh_stderr = worker.exec_command(actual_command, timeout=60, get_pty=True)  # Non-blocking call
        _, ssh_stdout, ssh_stderr = worker.exec_command(
            actual_command, get_pty=True
        )  # Non-blocking call
        result_out = ssh_stdout.read()
        result_err = ssh_stderr.read()
        exit_code = (
            ssh_stdout.channel.recv_exit_status()
        )  # Blocking call but only after reading it all
        # if random.randint(0, 10) > 5: # to force failure!
        #     exit_code = -1
        if not exit_code == 0:
            raise ErrorInGame(f"Error in running game - cmd: {actual_command}")
    except ErrorInGame:
        raise
    except Exception as e:
        job_secs_taken = datetime.datetime.now() - startTime
        logging.warning(f"TIME OUT in host {worker.hostname} ({job_secs_taken} secs. taken; {dest_dir}): {report_match(job)}")
        raise
    job_secs_taken = (
        datetime.datetime.now().replace(microsecond=0)
        - startTime.replace(microsecond=0)
    ).total_seconds()
    # if job_secs_taken < 3:
    #     print('Strange, game too short, something bad happened, failing it....')
    #     raise ErrorInGame('Error in running game - cmd: {}'.format(actual_command))
    time_games.append(job_secs_taken)

    logging.debug(
        f"END OF GAME in host {worker.hostname} ({dest_dir}) - START COPYING BACK RESULT: {report_match(job)}"
    )
    # Retrieve replay-0 and log-0 files produced in host to the local contest temporal folder
    # E.g., tf = TransferableFile(local_path='tmp/contest-a/replays-run/sklearn2_vs_waka_waka2_RANDOM6520.replay', remote_path='tmp/contest-a/replay-0')
    for tf in job.return_files:
        # print(tf)
        sftp.get(localpath=tf.local_path, remotepath=tf.remote_path)
    sftp.close()

    # clean temporary directory for the game in remote (e.g., /tmp/cluster_instance_sklearn2-vs-waka_waka2-in-RANDOM6520-2021-09-30-13-58-35/tmp/contest-a)
    worker.exec_command(f"rm -rf {dest_dir}")

    logging.info(
        f"FINISHED GAME in host {worker.hostname} ({job_secs_taken} time taken; {dest_dir}): {report_match(job)}"
    )
    logging.debug(
        f"FINISHED SUCCESSFULLY EXECUTING command in host {worker.hostname} dir {dest_dir}: {job.command}"
    )

    return job.data, exit_code, result_out, result_err, job_secs_taken


if __name__ == "__main__":
    """
    Little demo:
    - connects to localhost
    - executes for 10 times, using 2 processes in parallel, the following
      - copy the source of this script to the worker
      - sleep 1 second
      - trim the copied file keeping only the first line
      - add some stuff to the file
      - copy the file back to the directory of this script
    """
    hosts = [
        # prompt for password (for password authentication or if private key is password protected)
        Host(
            no_cpu=2,
            hostname="localhost",
            username=getuser(),
            password=getpass(),
            key_filename=None,
        )
        # use this if no pass is necessary (for private key authentication)
        # Host(no_cpu=2, hostname='localhost', username=getuser(), password=None, key_filename=None)
    ]
    jobs = []
    for i in range(10):
        instance_id = "".join(random.choice("0123456789abcdef") for _ in range(30))
        test_file = "%s.txt" % instance_id

        command = (
            "sleep 1; cat %s | head -1 > a.txt ; cat a.txt > %s ; ls -l >> %s ; echo ciao >> %s"
            % (test_file, test_file, test_file, test_file)
        )
        req_file = TransferableFile(
            local_path="cluster_manager.py", remote_path=test_file
        )
        ret_file = TransferableFile(local_path=test_file, remote_path=test_file)

        jobs.append(
            Job(
                command=command,
                required_files=[req_file],
                return_files=[ret_file],
                data=None,
                id="test",
            )
        )

    cm = ClusterManager(hosts=hosts, jobs=jobs)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cm.start()
