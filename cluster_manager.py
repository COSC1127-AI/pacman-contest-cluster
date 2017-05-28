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
import sys
from Queue import Queue
import random
import os
from thread_safe_file import ThreadSafeFile

# ----------------------------------------------------------------------------------------------------------------------
# Verify all necessary packages are present

missing_packages = []

try:
    # Used to prompt the password without echoing
    from joblib import Parallel, delayed
except:
    missing_packages.append('joblib')

try:
    # Used to prompt the password without echoing
    from getpass import getpass, getuser
except:
    missing_packages.append('getpass')

try:
    # Used to establish ssh connections
    from paramiko.config import SSHConfig
    from paramiko.client import SSHClient
    from paramiko.proxy import ProxyCommand
    from paramiko.sftp_client import SFTPClient
    from paramiko import AutoAddPolicy
except:
    missing_packages.append('paramiko')

if missing_packages:
    print('Some packages are missing. Please, run `pip install %s`' % ' '.join(missing_packages))
    if 'paramiko' in missing_packages:
        print('Note that you may need to install libssl-dev with `sudo apt-get install libssl-dev`')
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------
# Import class from helper module

Host = namedtuple('Host', ['no_cpu', 'hostname', 'username', 'password', 'key_filename'], verbose=False)
Job = namedtuple('Job', ['command', 'required_files', 'return_files', 'id'], verbose=False)
TransferableFile = namedtuple('TransferableFile', ['local_path', 'remote_path'], verbose=False)

stdout = ThreadSafeFile(sys.stdout)

class ClusterManager:
    def __init__(self, hosts, jobs):
        self.hosts = hosts  # type: 'List[Host]'
        self.jobs = jobs  # type: 'List[Job]'
        self.workers = []  # type: 'List[SSHClient]'
        self.pool = Queue()  # type: 'Queue[SSHClient]'

        total_no_workers = sum(host.no_cpu for host in hosts)
        # https: // pythonhosted.org / joblib / generated / joblib.Parallel.html
        self.workers = Parallel(total_no_workers, backend='threading')(delayed(create_worker)(host) for host in self.hosts for _ in range(host.no_cpu))
        for worker in self.workers:
            self.pool.put(worker)

    def start(self):
        results = Parallel(self.pool.qsize(), backend='threading')(delayed(run_job)(self.pool, job) for job in self.jobs)
        return results

    def start_single_threaded(self):
        results = [run_job(self.pool, job) for job in self.jobs]
        return results

def create_worker(host):
    config = SSHConfig()
    proxy = None
    if os.path.exists(os.path.expanduser('~/.ssh/config')):
        config.parse(open(os.path.expanduser('~/.ssh/config')))
        if host.hostname is not None and \
            'proxycommand' in config.lookup(host.hostname):
                proxy = ProxyCommand(config.lookup(host.hostname)['proxycommand'])

    # proxy = paramiko.ProxyCommand("ssh -o StrictHostKeyChecking=no e62439@131.170.5.132 nc 118.138.239.241 22")

    worker = SSHClient()
    worker.load_system_host_keys()
    worker.host = host.hostname  # store the host for later reference (e.g., logging)
    worker.set_missing_host_key_policy(AutoAddPolicy())
    # time.sleep(4)
    worker.connect(hostname=host.hostname, username=host.username, password=host.password, key_filename=host.key_filename, sock=proxy)
    return worker



def run_job(pool, job):
    worker = pool.get()
    try:
        return run_job_on_worker(worker, job)
    finally:
        pool.put(worker)

def run_job_on_worker(worker, job):
    # create remote env
    instance_id = ''.join(random.choice('0123456789abcdef') for _ in range(30))
    dest_dir = '/tmp/cluster_instance_%s' % instance_id
    sftp = worker.open_sftp()
    sftp.mkdir(dest_dir)
    sftp.chdir(dest_dir)
    for tf in job.required_files:
        sftp.put(localpath=tf.local_path, remotepath=tf.remote_path)

    # worker.host was stored when worker was created
    stdout.write('ABOUT TO EXECUTE command in host %s dir %s: %s' % (worker.host, dest_dir,  job.command))
    stdout.write('\n')

    # run job
    actual_command = """cd %s ; sh -c '%s'""" % (dest_dir, job.command)
    _, ssh_stdout, ssh_stderr = worker.exec_command(actual_command, get_pty=True)  # Non-blocking call
    result_out = ssh_stdout.read()
    result_err = ssh_stderr.read()
    exit_code = ssh_stdout.channel.recv_exit_status()  # Blocking call but only after reading it all

    # retrieve results
    for tf in job.return_files:
        sftp.get(localpath=tf.local_path, remotepath=tf.remote_path)

    # clean
    worker.exec_command('rm -rf %s' % dest_dir)

    stdout.write('FINISHED EXECUTING command in host %s dir %s: %s' % (worker.host, job.command, dest_dir))
    stdout.write('\n')

    return job.id, exit_code, result_out, result_err
    # return job.id, exit_code, ssh_stdout.read(), ssh_stderr.read()


if __name__ == '__main__':
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
        Host(no_cpu=2, hostname='localhost', username=getuser(), password=getpass(), key_filename=None)
        # use this if no pass is necessary (for private key authentication)
        # Host(no_cpu=2, hostname='localhost', username=getuser(), password=None, key_filename=None)
    ]
    jobs = []
    for i in range(10):
        instance_id = ''.join(random.choice('0123456789abcdef') for _ in range(30))
        test_file = "%s.txt" % instance_id

        command = "sleep 1; cat %s | head -1 > a.txt ; cat a.txt > %s ; ls -l >> %s ; echo ciao >> %s" % (test_file, test_file, test_file, test_file)
        req_file = TransferableFile(local_path='cluster_manager.py', remote_path=test_file)
        ret_file = TransferableFile(local_path=test_file, remote_path=test_file)

        jobs.append(Job(command=command, required_files=[req_file], return_files=[ret_file], id=None))

    cm = ClusterManager(hosts=hosts, jobs=jobs)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cm.start()
