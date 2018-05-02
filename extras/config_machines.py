from cluster_manager import Host, Job, TransferableFile, create_worker, run_job_on_worker
from joblib import Parallel, delayed
import os

CONFIG_PT1_FILENAME = 'config_pt1.sh' # to be run as root
CONFIG_PT2_FILENAME = 'config_pt2.sh' # to be run as user, in his/her home
USER = 'seba'
USER_HOME = '/home/seba'
USER_PRIVATE_KEY_FILE_PATH = '/home/marco/id_seba'
USER_PUBLIC_KEY_FILE_PATH = '/home/marco/id_seba.pub'


COMMANDS_PT1 = """
#!/usr/bin/env bash

# deluser seba

if id {user} >/dev/null 2>&1; then
    echo "User {user} exists already"
else
    echo "Creating user"
    rm -rf /home/{user}/
    adduser --disabled-password --gecos "" {user}
fi

echo "Configuring private key authentication"
mkdir -p /home/{user}/.ssh/
cat {public_key_filename} > /home/{user}/.ssh/authorized_keys
chown -R {user} /home/{user}/
echo "All done"

""".format(user=USER, public_key_filename=os.path.basename(USER_PUBLIC_KEY_FILE_PATH))


COMMANDS_PT2 = """
#!/usr/bin/env bash

if [ ! -d ~/miniconda/ ]; then
    echo "Installing Conda"
    wget -nv https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda/
else
    echo "Conda already installed"
fi

PATH=$PATH:~/miniconda/bin

if [ `conda env list | grep -o py2 | wc -l` -eq 0 ]; then
    echo "Creating Conda environment"
    conda create -y -n py2 python=2
    echo "All done"
else
    echo "Conda environment already setup"
fi

echo "Setting up Conda environment"
~/miniconda/bin/pip install -q numpy pandas scipy tabulate joblib paramiko iso8601 pytz
echo "All done"

"""

with open(CONFIG_PT1_FILENAME, 'w') as f:
    f.write(COMMANDS_PT1)

with open(CONFIG_PT2_FILENAME, 'w') as f:
    f.write(COMMANDS_PT2)

private_key_filename = '/home/marco/.ssh/id_rsa'

def config_host(sudoer_user, hostname):
    # print('Connecting to {hostname} as {user}'.format(hostname=hostname, user=sudoer_user))
    host_as_sudoer = Host(no_cpu=4, hostname=hostname, username=sudoer_user, password=None, key_filename=private_key_filename)
    worker_as_sudoer = create_worker(host_as_sudoer)
    job1 = Job(
        command='sudo bash {config_pt1_filename}'.format(config_pt1_filename=CONFIG_PT1_FILENAME, user=USER),
        required_files=[
            TransferableFile(local_path=CONFIG_PT1_FILENAME, remote_path=CONFIG_PT1_FILENAME),
            TransferableFile(local_path=USER_PUBLIC_KEY_FILE_PATH, remote_path=os.path.basename(USER_PUBLIC_KEY_FILE_PATH))
        ],
        return_files=[],
        id=None
    )
    _, _, out_pt1, err_pt1, _ = run_job_on_worker(worker_as_sudoer, job1)
    with open('log_{hostname}_pt1.txt'.format(hostname=hostname), 'w') as f:
        f.write(out_pt1 + err_pt1)

    # print('Connecting to {hostname} as {user}'.format(hostname=hostname, user=USER))
    host_as_new_user = Host(no_cpu=4, hostname=hostname, username=USER, password=None, key_filename=USER_PRIVATE_KEY_FILE_PATH)
    worker_as_new_user = create_worker(host_as_new_user)
    job2 = Job(
        command='bash {config_pt2_filename}'.format(config_pt2_filename=CONFIG_PT2_FILENAME, user=USER),
        required_files=[
            TransferableFile(local_path=CONFIG_PT2_FILENAME, remote_path=CONFIG_PT2_FILENAME)
        ],
        return_files=[],
        id=None
    )
    _, _, out_pt2, err_pt2, _ = run_job_on_worker(worker_as_new_user, job2)
    with open('log_{hostname}_pt2.txt'.format(hostname=hostname), 'w') as f:
        f.write(out_pt2 + err_pt2)






import paramiko
paramiko.util.log_to_file("filename.log")

# config_host('ubuntu', '118.138.244.72')


with open('my_workers.txt', 'r') as f:
    hostnames = [(line.split('@')[0].strip(), line.split('@')[1].strip(), line.split('@')[2].strip()) for line in f.readlines()]

# Multi-threaded
results = Parallel(len(hostnames), backend='threading')(delayed(config_host)(user, hostname) for _, user, hostname in hostnames)

# results = []
# for user, hostname in hostnames:
#     results.append(config_host(user, hostname))

# print(''.join(out + err for out, err in results))







# Clean
os.remove(CONFIG_PT1_FILENAME)
os.remove(CONFIG_PT2_FILENAME)
