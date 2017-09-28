# PACMAN CONQUER THE FLAG - CONTEST SUPPORT SCRIPT #

This script can be used to run a Berkley Pacman Conquer the Flag Contest (http://ai.berkeley.edu/contest.html)

Developed for RMIT COSC1125/1127 AI course in 2017 (lecturer A/Prof. Sebastian Sardina; support: Marco Tamassia), based on an original script from Dr. Nir Lipovetzky developed for UNIMELB COMP90054 AI course in 2014, and adapted in 2017 to work at Unimelb after RMIT refactoring and extensions.

CONTACT: Sebastian Sardina (ssardina@gmail.com) and Nir Lipovetzky (nirlipo@gmail.com)

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


* Each team is a .zip file; they should all go in a directory (e.g., teams/)
    * the agent system is in the root of the zip file
    * [optional to run with --team-names-file] zip file should start with "s", continue with student number, then _, and then date in iso8601 format (https://en.wikipedia.org/wiki/ISO_8601), then .zip
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
sudo pip install -r requirements.txt
sudo pip install -U  paramiko
```


Hence, user must provide:

- private keys for cluster (if needed; specified in workers.json)
- Directory with set of zip submission files; see above (for option --teams)
- workers.json: listing the cluster setting to be used (for option --workers-file-path)
- TEAMS-STUDENT-MAPPING.csv [optional]: a csv mapping submissions to teams (for option --team-names-file)
    - Main columns are: STUDENT_ID and TEAM_NAME
    - If **no file provided**, teamnames are taken from the submitted zip files (this is the option used at unimelb)



## HOW THE SCRIPT WORKS ##


### Main components: ###

- unimelb_dimefox_script.py: downloads teams from submissions server, runs pacman-ssh-contest.py and upload results into the web.
- pacman-ssh-contest.py: main script
- cluster_manager.py: the script to manage clusters
- contest.zip: the actual main contest infrastructure, based on that one from UC (with minor fixes, e.g., delay in replays)
- layouts.zip: some interesting layouts that can be used (beyond the randomly generated ones)
- staff_team_{basic,medium,top}.zip: the teams from staff, used for --include-staff-team option
- contest/ subdir: developing place for contest.zip. The .zip file should contain all files in the root of the .zip
- TEAMS-STUDENT-MAPPING.csv: example of a mapping file


### Overview of marking process: ###

1. The script authenticate to all workers.
2. Then the script will collect all the teams, as per _--teams-root_ option. 
- If option **--ignore-file-name-format** is given, then it will simply collect the teamnames from the <teamname>.zip files, otherwise:
    - Will collect each file with pattern s<student number>_<timestamp>.zip
    - If student number is not registered in any team as per mapping given by _--team-names-file_ then the file is 
    ignored (we do not know which team it corresponds) and the following message is issued:
        ````
        Sun, 24 Sep 2017 15:25:48 WARNING  Student not registered: "s123456" (file test-teams/s123456_2017-05-15). Skipping
        ````
    - If student is found in a team but submission has wrong timestamp, then it is also ignored as we cannot know if it 
    is the latest submission for the team. A message is issued:
        ````
        Sun, 24 Sep 2017 15:25:48 WARNING  Team zip file "test-teams/s5433273" name has invalid date format. Skipping
        ````
3. The script will _use contest.zip_, _layouts.zip_ (where some fixed layouts are stored) and a set of teams and:
    1. create a temporary full contest dir _contest-tmp_
    2. zip it into _contest_and_teams.zip_ file
3. For each game:
    1. transfer  _contest_and_teams.zip_ to an available worker
    2. expanded in /tmp/cluster_xxxxxxx
    3. run game
    4. copy back log and replay to marking machine. 
    


### Example of a run: ###
Using a csv file to specify teams:
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
Collecting submitted files in teams, and using the zip filename as teamname:
````
python pacman-ssh-contest.py --compress-log --organizer RMIT \
                        --teams-root test-teams/ \ 
                        --output-path test-www/ \ 
                        --max-steps 1200 \
                        --include-staff-team \
                        --no-fixed-layouts 3 \
                        --no-random-layouts 5 \
                        --ignore-file-name-format \
                        --workers-file-path my_workers-nectar.json
````

### Schedule competition to run at midnight ###


If you want to automate the tournament, use the driver.py provided. It has the following options:

```
  --username [USERNAME]
                        username for --teams-server-url
  --password [PASSWORD]
                        password for --teams-server-url
  --dest-www [DEST_WWW]
                        Destination folder to publish www data in a web
                        server. (it is recommended to map a web-server folder
                        using smb)
  --teams-server-folder [TEAMS_SERVER_FOLDER]
                        folder containing all the teams submitted at the
                        server specified at --teams-server-name
  --teams-server-url [TEAMS_SERVER_URL]
                        server address containing the teams submitted
  --tournament-cmd [TOURNAMENT_CMD]
                        specify all the options to run pacman-ssh-contesy.py
  --cron-script-folder [CRON_SCRIPT_FOLDER]
                        specify the folder to the scripts in order to run cron
```

=======

Run the following command:
```
crontab -e
```
and introduce the following line into the *cronfile*
```
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

01 00 * * * python driver.py --username xxx --password xxx --cron-script-folder ''  --dest-www '' --teams-server-folder '' --teams-server-url xxx --tournament-cmd ''
```

Now your script will run every midnight at 00:01

