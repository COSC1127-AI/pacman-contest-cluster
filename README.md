# PACMAN CONQUER THE FLAG - CONTEST SUPPORT SCRIPT #

This script can be used to run a Berkley Pacman Conquer the Flag Contest (http://ai.berkeley.edu/contest.html)

Developed for RMIT COSC1125/1127 AI course in 2017 (lecturer A/Prof. Sebastian Sardina; support: Marco Tamassia), based on an original script from Dr. Nir Lipovetzky.

CONTACT: Sebastian Sardina (ssardina@gmail.com)

## OVERVIEW ##

This system allows to run a full Pacman Conquer the Flag tournament among many teams using a cluster of machines. This means that it allows to run many games at the same time, depending how many total cpu cores are available.

The system takes the set of teams, set of workers in a cluster, and tournament configuration (which layouts and how many steps per game) and runs games for every pair of teams and layouts.

To see options available run: 
    _python pacman-ssh-contest.py --help_


### Features ###

* Cluster support to run many games at the same time.
    * option --workers-file-path <json file>
    * connection via ssh with tunneling support if needed.
* Can use variable number of fixed layouts and randomly generated layouts.
    * options --no-fixed-layouts and --no-random-layouts 
* Flexible configuration via many command line options.
* Map individual student submissions to teams.
    * Via student-team mapping file; option --team-names-file
* Generate HTML page with tournament results and list of replay files.
    * option --output-path
* Handle latest submission by sorting via timestamp in file name.
    * all members of a team can submit at any point
    * last submission per team is considered (if there are multiple)
    * this is done by mapping individual submission to a team via --team-names-file and timestamp in zip submission file 
    
    
## PRE-REQUISITES ##

* unzip & zip (to pack and unpack submissions and files for transfer)
* Python >=2.7
    * python-future
    * future
    * iso8601
    * pytz
    * paramiko


* Each teams is a .zip file; they should all go in a directory (e.g., teams/)
    * the agent system is in the root of the zip file
    * zip file should start with "s", continue with student number, then _, and then date in iso8601 format (https://en.wikipedia.org/wiki/ISO_8601), then .zip
        * format stored regexp SUBMISSION_FILENAME_PATTERN: r'^(s\d+)_(.+)?\.zip$'
        * Examples of legal files:
            - s2736172_2017-05-13T21:32:43.342000+10:00.zip
            - s2736172_2017-05-13.zip

* The cluster to be used is specified with option --workers-file-path, to point to a .json file containing the workers
available (including no of cores, IP, username, password, and private key file if needed)

* Cluster should have all the Python and Unix packages to run the contest. For example, in the NeCTAR cluster I ran:

```
sudo apt-get update
sudo apt-get install python-pip unzip
pip install -r requirements.txt
```


Hence, user must provide:

- private keys for cluster (if needed; specified in workers.json)
- Directory with set of zip submission files; see above (for option --teams)
- workers.json: listing the cluster setting to be used (for option --workers-file-path)
- TEAMS-STUDENT-MAPPING.csv: a csv mapping submissions to teams (for option --team-names-file)
    - Main columns are: STUDENT_ID and TEAM_NAME



## HOW THE SCRIPT WORKS ##


### Main components: ###

- pacman-ssh-contest.py: main script
- cluster_manager.py: the script to manage clusters
- contest.zip: the actual main contest infrastructure, based on that one from UC (with minor fixes, e.g., delay in replays)
- layouts.zip: some interesting layouts that can be used (beyond the randomly generated ones)
- staff_team.zip: the team from the staff, used for --include-staff-team option
- contest/ subdir: developing place for contest.zip. The .zip file should contain all files in the root of the .zip
- TEAMS-STUDENT-MAPPING.csv: example of a mapping file


### Overview of marking process: ###

1. The script authenticate to all workers.
2. The script will _use contest.zip_, _layouts.zip_ (where some fixed layouts are stored) and a set of teams and:
    1. create a temporary full contest dir _contest-tmp_
    2. zip it into _contest_and_teams.zip_ file
3. For each game:
    1. transfer  _contest_and_teams.zip_ to an available worker
    2. expanded in /tmp/cluster_xxxxxxx
    3. run game
    4. copy back log and replay to marking machine. 
    


### Example of a run: ###

````
python pacman-ssh-contest.py --compress-log --organizer RMIT \
                        --teams-root test-teams/ \ 
                        --output-path test-www/ \ 
                        --max-steps 1200 \
                        --team-names-file AI17-Contest-TEAMS.csv \
                        --include-staff-team \
                        --no-fixed-layouts 3 \
                        --no-random-layouts 5 \
                        --workers-file-path my_workers-nectar.json
````