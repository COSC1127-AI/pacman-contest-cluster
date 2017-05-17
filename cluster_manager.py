from collections import namedtuple
import sys
from Queue import Queue
import random
import os

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
    from paramiko.client import SSHClient
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
Job = namedtuple('Job', ['command', 'required_files', 'return_files'], verbose=False)
TransferableFile = namedtuple('TransferableFile', ['local_path', 'remote_path'], verbose=False)

class ClusterManager:
    def __init__(self, hosts, jobs):
        self.hosts = hosts  # type: 'List[Host]'
        self.jobs = jobs  # type: 'List[Job]'
        self.workers = []  # type: 'List[SSHClient]'
        self.pool = Queue()  # type: 'Queue[SSHClient]'
        for host in self.hosts:
            for i in range(host.no_cpu):
                worker = SSHClient()
                worker.load_system_host_keys()
                worker.set_missing_host_key_policy(AutoAddPolicy())
                worker.connect(hostname=host.hostname, username=host.username, password=host.password, key_filename=host.key_filename)
                self.workers.append(worker)
                self.pool.put(worker)

    def start(self):
        results = Parallel(self.pool.qsize(), backend='threading')(delayed(run_job)(self.pool, job) for job in self.jobs)
        return results

def run_job(pool, job):
    worker = pool.get()
    try:
        print('Executing command: %s' % job.command)

        # create remote env
        instance_id = ''.join(random.choice('0123456789abcdef') for _ in range(30))
        dest_dir = '/tmp/cluster_instance_%s' % instance_id
        sftp = worker.open_sftp()
        sftp.mkdir(dest_dir)
        sftp.chdir(dest_dir)
        for tf in job.required_files:
            sftp.put(localpath=tf.local_path, remotepath=tf.remote_path)

        # run job
        actual_command = """cd %s ; sh -c '%s'""" % (dest_dir, job.command)
        _, ssh_stdout, _ = worker.exec_command(actual_command)  # Non-blocking call
        exit_code = ssh_stdout.channel.recv_exit_status()  # Blocking call

        # retrieve results
        for tf in job.return_files:
            sftp.get(localpath=tf.local_path, remotepath=tf.remote_path)

        # clean
        worker.exec_command('rm -rf %s' % dest_dir)

        return exit_code, ssh_stdout.read()

    finally:
        pool.put(worker)


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
        Host(no_cpu=2, hostname='localhost', username=getuser(), password=getpass(), key_filename=None) # prompt for password (for password authentication or if private key is password protected)
        # Host(no_cpu=2, hostname='localhost', username=getuser()', password=None, key_filename=None) # use this if no pass is necessary (for private key authentication)
    ]
    jobs = []
    for i in range(10):
        instance_id = ''.join(random.choice('0123456789abcdef') for _ in range(30))
        test_file = "%s.txt" % instance_id

        command = "sleep 1; cat %s | head -1 > a.txt ; cat a.txt > %s ; ls -l >> %s ; echo ciao >> %s" % (test_file, test_file, test_file, test_file)
        req_file = TransferableFile(local_path='cluster_manager.py', remote_path=test_file)
        ret_file = TransferableFile(local_path=test_file, remote_path=test_file)

        jobs.append(Job(command=command, required_files=[req_file], return_files=[ret_file]))

    cm = ClusterManager(hosts=hosts, jobs=jobs)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cm.start()
