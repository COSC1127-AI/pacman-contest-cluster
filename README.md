# PACMAN CAPTURE THE FLAG - CONTEST SCRIPT

This system runs complex contests for the [UC Berkley Pacman Conquer the Flag](http://ai.berkeley.edu/contest.html) game.

Designed & developed for RMIT COSC1125/1127 AI course in 2017 by lecturer A/Prof. Sebastian Sardina (with programming support by Marco Tamassia), based on an original script from Dr. Nir Lipovetzky. Since then, the tool has been continuously improved and extended to fit RMIT COSC1125/1127 and UNIMELB COMP90054 AI course.

The system runs on Python 3.x. Currently used on Python 3.6.

**CONTACT:** Prof. Sebastian Sardina (ssardina@gmail.com) and Dr. Nir Lipovetzky (nirlipo@gmail.com)

Table of Contents
=================

- [PACMAN CAPTURE THE FLAG - CONTEST SCRIPT](#pacman-capture-the-flag---contest-script)
- [Table of Contents](#table-of-contents)
  - [OVERVIEW](#overview)
    - [Features](#features)
    - [Setup & Dependencies](#setup--dependencies)
      - [Worker machines](#worker-machines)
      - [Central Script Host](#central-script-host)
      - [Web-server configuration](#web-server-configuration)
  - [MAIN COMPONENTS](#main-components)
  - [OVERVIEW OF MARKING PROCESS](#overview-of-marking-process)
  - [EXAMPLE RUNS](#example-runs)
    - [Run a contest](#run-a-contest)
    - [Run contest only vs staff teams](#run-contest-only-vs-staff-teams)
    - [Run a multi/split contest](#run-a-multisplit-contest)
    - [Resume partial contest](#resume-partial-contest)
    - [Re-run only some teams in a given contest](#re-run-only-some-teams-in-a-given-contest)
    - [Re-run only updated teams](#re-run-only-updated-teams)
  - [WEB PAGE GENERATION](#web-page-generation)
    - [Interactive Dashboard](#interactive-dashboard)
    - [Schedule contest runs](#schedule-contest-runs)
  - [MODIFYING THE CONTEST GAME](#modifying-the-contest-game)
  - [TROUBLESHOOTING](#troubleshooting)
  - [SCREENSHOT](#screenshot)
  - [LICENSE](#license)

----------------------

## OVERVIEW

This system runs a full Pacman Capture the Flag tournament among many teams using a _cluster of machines/CPUs_ (e.g., [Australia's NeCTAR](https://nectar.org.au/).

The contest script takes a set of teams, a set of machine workers in a cluster, and a tournament configuration (which layouts and how many steps per game), and runs games concurrently (one per worker) for every pair of teams and layouts (round-robin type of tournament), and produces files and html web page with the results. With `n` teams playing on `k` layouts there will be `(n(n-1) / 2)k` games. To deal with too many teams, the script can play teams against staff team systems only and also split teams into random sub-contests and run them in sequence.

The system contains two main scripts:

1. ```pacman_contest_cluster.py``` is the main script to actually run a contest.
2. ```pacman_html_generator.py``` generates an HTML web page from existing data of already ran contests.

To see options available run:

```bash
python3  pacman_contest_cluster.py -h
```

```bash
python3 pacman_html_generator.py --h
```

### Features

- Build `n` subcontests where teams are assigned randomly to one of them (`--split` option).
- Play teams only against staff teams.
- Runs multiple games at the same time by using a cluster of worker machines/CPUs.
  - option `--workers-file <json file>`
  - connection via ssh with tunneling support if needed.
- Able to use variable number of fixed layouts and randomly generated layouts.
  - options `--no-fixed-layouts` and `--no-random-layouts`
- Generate an HTML page with the contest result and full details, including links to replay files.
  - Ability to store replays and logs into [`https://transfer.sh`](https://transfer.sh) service to avoid filling local www space.
  - Ranking generation: 3 points per win; 1 point per tie. Failed games are loses. Ordered by: points first, no. of wins second, score points third.
- Handle latest submission per team, by sorting via timestamp recorded in file name.
- Can resume a partial ran contest or extend an existing contest.
- Save options into a JSON file `config.json` for future runs using `--build-config-file` option.

### Setup & Dependencies

#### Worker machines

- unzip & zip commands (to pack and unpack submissions and files for transfer)
  - `sudo apt-get install -y unzip zip vim`
- Python 3.x with standard libraries.
  - The original UC Pacman Contest ran under Python 2, but in this system it was ported to version 3.
- Set the SSH server to accept as many connections as you want to run concurrently. This is done by changing option `MaxStartups` in file `/etc/ssh/sshd_config`. By default `sshd` has up to 10 connections.
  - For example, set `MaxStartups 100:30:100` to accept up to 100 simultaneous connections. Remember to restart the ssh server: `sudo service sshd restart`
  - For more info on this, see issue [#26](https://github.com/AI4EDUC/pacman-contest-cluster/issues/26).
- Cluster should have all the Python and Unix packages to run the contest. For example, in the [NeCTAR cluster](https://ardc.edu.au/services/nectar-research-cloud/):

    ```bash
    sudo apt-get update
    sudo apt-get install python3-pip unzip vim
    sudo pip3 install setuptools

    wget https://raw.githubusercontent.com/AI4EDUC/pacman-contest-cluster/master/requirements.txt
    python -m pip install --user --upgrade pip
    sudo pip3 install -r requirements.txt
    ```

    If you do not have root access you can use `pip install -r requirements.txt --user` to do a user install. Get [requirements.txt](requirements.txt) with wget.

- Many students benefit from the availability other tools, like [TensorFlow](https://www.tensorflow.org/), [scikit-learn](http://scikit-learn.org/), [neat-python](https://github.com/CodeReclaimers/neat-python):

    ```shell
    pip3 install tensorflow sklearn scipy neat-python --user
    ```

- If students want to use planners to solve pacman PDDL models for their solutions, copy any planner to `/usr/local/bin`. For example, in the NeCTAR cluster:

  ```shell
    sudo cp planners/ff /usr/local/bin/.
  ```

#### Central Script Host

In the **local machine** (e.g., your laptop) that will dispatch game jobs to the cluster via the `pacman_contest_cluster.py` script:

- unzip & zip (to pack and unpack submissions and files for transfer): `sudo apt-get install -y unzip zip`
- Python >= 3.5 with:
  - setuptools
  - iso8601
  - pytz
  - paramiko

- Simply run: `pip3 install -r requirements.txt --user`

In addition to that:

- Each submission is a `.zip` file or a directory; all within some folder (e.g., `teams/`)
  - The player agent should be in the _root_ of the team zip file or team directory.
  - Submission file/dir name will be used as the team name.
  - zip/dir should start with "`s`", continue with student number, then `_`, and then date in [iso8601 format](https://en.wikipedia.org/wiki/ISO_8601), then `.zip`
  - Format stored regexp `SUBMISSION_FILENAME_PATTERN`: `r'^(s\d+)_(.+)?\.zip$'`
  - Examples of legal team zip files:
    - `s2736172_2017-05-13T21:32:43.342000+10:00`
    - `s2736172_2017-05-13.zip`
  - Examples of team directories:
    - `Destructor_Pacman-05-13T21:32:43.342000+10:00`
    - `WeWillWin-05-13`
  - The student number will be mapped to a team and the timestamp will be used to pick the latest team submission.

- The cluster to be used is specified with option `--workers-file-path`, to point to a `.json` file containing the workers available (including no of cores, IP, username, password, and private key file if needed)

Hence, the user of this system must provide:

- *private keys* for cluster (if needed; specified in `workers.json`).
- Directory with set of zip submission files; see above (for option `--teams`)
- `workers.json`: listing the cluster setting to be used (for option `--workers-file-path`)
- `TEAMS-STUDENT-MAPPING.csv` [optional]: a CSV mapping student ids to team names (for option `--team-names-file`)
  - Main columns are: `STUDENT_ID` and `TEAM_NAME`
  - If no file provided is provided, team names are taken directly from the submitted zip files (this is the option used at unimelb).

#### Web-server configuration

Install Apache web-server first:

```shell
$ sudo apt-get install apache2
```

The default Ubuntu document root is `/var/www/html`, so it first serve  `/var/www/html/index.html` when accessing the server.

A very easy way to serve multiple folders elswhere is to create symbolic links from there to the root of your site. For example:

```shell
$ sudo ln -s /home/ssardina/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/www/ /var/www/html/prelim
```

To set-up the web-page for preliminary contests at `http://<ip server>/prelim`

To allow directory listing and configure per directory, first disable listig by default by changing `/etc/apache/apache2.conf` as follows:

```sml
<Directory /var/www/>
        #Options Indexes FollowSymLinks
        Options FollowSymLinks
        AllowOverride all
        Require all granted
</Directory>
```

The key here is to disable out `Indexes` and `FollowSymLinks` by default, and allow overrriding via `.htaacess` files with `AllowOverride all`.

Then, to allow listing in a folder, add `.htaccess` file (permission `0755`) there with:

```
Options Indexes FollowSymLinks
IndexOptions FancyIndexing FoldersFirst NameWidth=* DescriptionWidth=*
```

NOTE: One could install the lighter Lighttpd web-server, but it happens that it does not use `.htaccess` so it is more difficult to set-up per directory listing.

## MAIN COMPONENTS

The main script `pacman_contest_cluster.py` runs a full contest and uses:

- `cluster_manager.py`: the support script to manage clusters (used by `pacman_contest_cluster.py`).
- `contest.zip`: the actual main contest infrastructure, based on that one from UC (with minor fixes, e.g., delay in replays, upgraded to Python 3.x)
- `layouts.zip`: some interesting layouts that can be used (beyond the randomly generated ones)
- `staff_team_{basic,medium,top}.zip`: the teams from staff, used for `--include-staff-team` option.
  - You can point to the directory containing all three staff agents using `--staff-teams-roots` (default is current dir)
  - You can use your own basic, medium, top agents, as long as they are named accordingly.  
  - If you want to use our agents, co ntact us. These teams are not shared as they are used for marking purposes. So, if
     you get access to them, please do not distribute.
- `TEAMS-STUDENT-MAPPING.csv`: example of a mapping file
- `contest/` folder: developing place for `contest.zip`.
- `extras/` folder: additional scripts and resources; some of them may be out-dated.

## OVERVIEW OF MARKING PROCESS

In a nutshell, the script follows the following steps:

1. Authenticates to all workers specified.
2. Collect all the teams.
    - If option `--ignore-file-name-format` is given, then it will simply collect the team names from the `<team-name>.zip` files.
    - Otherwise, it will assume a file name `s<team-name>_<timestamp>.zip`. 
3. Take `contest.zip`, `layouts.zip` (where some fixed layouts are stored), and the set of collected set of teams and:
    1. create a temporary full contest dir `contest-tmp`;
    2. zip it into `contest_and_teams.zip` file;
    3. transfer  `contest_and_teams.zip` to each available worker.
4. For each game:
    1. expand in `contest_and_teams.zip` to `/tmp/cluster_xxxxxxx`;
    2. run game;
    3. copy back log and replay to marking machine.
5. Produce stat files as JSON files (can be used to generate HTML pages).

The full contest is **all-against-all tournament** with the following rank generation:

- 3 points per win; 1 point per tie; 0 points per lose. Failed games are loses.
- Ordered by: points first, no. of wins second, score points third.

## EXAMPLE RUNS

### Run a contest

Using a CSV file to specify team names, include staff teams:

````shell
$ python3  pacman_contest_cluster.py --compress-log \
        --organizer "RMIT COSC1125/1127 - Intro to AI" \
        --teams-roots AI17-contest/teams1/ AI17-contest/teams2/  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 10 \
        --workers-file AI1-contest/workers/nectar-workers.jason  
        --staff-teams-roots AI17-contest/staff-teams/
````

Collecting submitted files in teams, and using the zip filename as teamname, and uploading the replays file only into a sharing file service instead of your local directory:

````shell
$ python3  pacman_contest_cluster.py --compress-log \
        --organizer "UoM COMP90054/2018 - AI Planning" \
        --teams-roots AI17-contest/teams/  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 10 \
        --workers-file AI1-contest/workers/nectar-workers.jason  
        --staff-teams-roots AI17-contest/staff-teams/
        --upload-www-replays
````

### Run contest only vs staff teams

To make the teams play only the staff teams (but not between them), use the  `--staff-teams-vs-others-only` option.

To hide the staff teams from the final leaderboard table, use `--hide-staff-teams`.

Finally, one can higlight different levels of performance using option `--score-thresholds`.

### Run a multi/split contest

When having too many teams, you can use the `--split n` option to generate `n` balanced contests from the pool of teams. Each team will be assigned randomly to one contest. Sub-contests will have the timestamp but a letter as suffix, e.g., `A`, `B`, etc.

For example, to run a split multi-contest with 5 sub-contests use `--split 5`.

### Resume partial contest

It is possible to **resume** an existing failed/partial competition or **repeat** a specific competition by using the option `--resume-contest-folder`.

So, if a run fails and is incomplete, all the logs generated so far can be found in the folder ``tmp\logs-run`` in your the local machine cloned repo.

To _resume_ the competition (so that all games played are used and not re-played):

1. Copy the temporal files into a different temporal folder: `mv tmp tmp-failed`. 
   * This is important, the folder `tmp/` as is cannot be used as it will be re-generated for each contest.
2. Tell the script to use that folder to get the existing logs by appending `--resume-contest-folder tmp-failed/` and the configuration file stored in that existing contest:

```shell
$ python pacman-contest-cluster.git/pacman_contest_cluster.py  --resume-contest-folder tmp-failed
```

This will run the exact configuration used in the contest being resumed by reading and using saved configuration `tmp-failed/config.json`. 

To extend an existing contest with more layout games, use options `--no-fixed-layouts` and `--no-random-layouts` with greater numbers than the one in the contest done. For example, if the contest in `tmp-failed/` included 2 fixed and 3 random layouts, we can extend it with more one more of each type as follows:

```shell
$ python pacman-contest-cluster.git/pacman_contest_cluster.py --no-random-layouts 3 --no-fixed-layouts 4 --resume-contest-folder tmp-failed
```

This will add one more fixed and one more random layout, both chosen randomly.

If you want to control exactly which fixed or random layout to add, then use options `--fixed-layout-seeds` and `--random-layout-seeds`. This will force the script to use specific layouts (look in folder [layouts/](layouts/) for available fixed, non-random, layouts). 
* When using these options, the information stored in the previous contest configuration file on which layouts were used will be disregarded. 
* Thus, one has to specify ALL the layouts that the new contest must use, including the previous ones and the specific ones one wants to add. 
* If the seeds given are less than the number of layouts asked for, the remaining are completed randomly.

For example, if the previous contest used `contest05Capture` and `contest16Capture` fixed layouts and `7669,1332,765`, one can extend it further with specific layouts `contest20Capture` and `1111` as follows:

```shell
$ python pacman-contest-cluster.git/pacman_contest_cluster.py --no-random-layouts 3 --no-fixed-layouts 4 --fixed-layout-seeds contest05Capture,contest16Capture,contest20Capture --random-layout-seeds 7669,1332,765,1111 --resume-contest-folder tmp-failed
```

Remember the seeds of the layouts used in the previous contests are always saved in file `config.json`. It can also be manually extracted from log file names as follows:

1. For the random seeds:

    ```bash
    $ ls -la tmp-failed/logs-run/ |  grep RANDOM | sed -e "s/.*RANDOM\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```

2. For the fixed layouts:

    ```bash
    $ ls -la tmp-failed/logs-run/ |  grep -v RANDOM | grep log | sed -e "s/.*_\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```

### Re-run only some teams in a given contest

If only one or a few teams failed, one can just re-run those ones by basically deleting their logs from the temporary folder and re-running/resuming a contest as above.

To delete the logs of a given team:

```bash
$ find tmp-failed -name \*<TEAM NAME>\*.log -delete
```

When resuming the contest in `tmp-failed/`, it will only run the games for the logs you just deleted.


### Re-run only updated teams

One quick and good strategy is to run a big contest but re-playing all games where one of the teams was updated.

To do so, we use the above method but we first delete all the logs of the teams that have been updated:

```bash
$ for d in `cat ai20-contest-timestamps.csv | grep updated | awk -F "\"*,\"*" '{print $1}'` ; do find tmp-failed/contest-a/logs-run/ -name \*$d*.log ; done
```

This takes advantage of the cloning script that leaves a column in the csv file stating whether the repo was updated or not from the last cloning.

## WEB PAGE GENERATION

A contest will leave JSON files with all stats, replays, and logs, from which a web page can be produced.

For example, to build web page in `www/` from stats, replays, and logs dirs:

```shell
$ python3 pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" \
    --www-dir www/ \
    --stats-archive-dir stats-archive/  \
    --replays-archive-dir replays-archive/ \ 
    --logs-archive-dir logs-archive/
```

or if all stats, replays, and logs are within `www/` then just:

```shell
$ python3 pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" --www-dir www/
```

**Observation:** If the stats file for a run has the `transfer.sh` URL for logs/replays, those will be used.

### Interactive Dashboard

As of 2020, the system includes a pretty visual dashboard that can display the results of the various contests carried out in an interactive manner. Students can select which teams to display, and compare selectively.

The dashboard will be served as a web-server, by default on port 8501.

See `/dashboard/` folder for more information how to set-it up and run the dashboard system.

### Schedule contest runs

It is convenient to set-up a script that will update all repos and then run a contest. This script can then be scheduled to run every day.

First, here is a template script `run-contest.sh`:

```shell
#!/bin/bash

now=`date +"%Y-%m-%d--%H-%M"`
log_file="contest-${now}.log"

SUBMISSIONS=submissions
TAG=testing
WWW=www-test
DESCRIPTION="RMIT COSC1127/1125 AI'21 (Prof. Sebastian Sardina) - Feedback Contest"
RANDOM_LAYOUTS=$2
FIXED_LAYOUTS=$1

cd /mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/preliminary

python ../../../git-hw-submissions.git/git_clone_submissions.py --file-timestamps pc-timestamps.csv pc-repos.csv $TAG $SUBMISSIONS  >> $log_file 2>> $log_file

echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>" >> $log_file

python  ../pacman-contest-cluster.git/pacman_contest_cluster.py --organizer "$DESCRIPTION"  --www-dir $WWW  --max-steps 1200 --no-fixed-layouts $FIXED_LAYOUTS --no-random-layouts $RANDOM_LAYOUTS --build-config-file config-feedback.json  --workers-file ../workers-nectar21.json --staff-teams-vs-others-only  --hide-staff-teams --score-thresholds 25 38 53 88 --teams-roots $SUBMISSIONS --staff-teams-roots ../reference-contest/reference-teams >> $log_file 2>> $log_file
```

To run it interactively:

```shell
$ ./run-contest.sh 5 4
```

We can then schedule it via **cron**. To do that, run the following command

```shell
crontab -e
```

and introduce the following line:

```shell
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

01 00 * * * <path/to/script/>run-contest.sh 5 10
```

Now your script will run every midnight at 00:01 and a log will be left.

## MODIFYING THE CONTEST GAME

The code implementing a game simulator between two players is located in `contest/` as a _git submodule_ from [pacman-contest-agent](https://github.com/AI4EDUC/pacman-contest-agent) repository, which also serves as an empty agent template.

As of 2019, that code runs under Python 3.x. The game simulator for Python 2.7 is kept in repository [pacman-contest-27](https://github.com/AI4EDUC/pacman-contest-27/) repository.

Note that the submodule source under `contest/` is NOT used for the actual cluster tournament, which only uses the source packed in `contest.zip` file.

It is however left there under `contest/` just in case one wants to run and test specific single games, if needed. For example, if we assume that `contest/teams` points to a set of teams, we can run one game as follows:

```bash
$ cd contest/
$ python3 capture.py -r teams/staff_team_super/myTeam.py -b teams/staff_team_medium/myTeam.py
```

Remember that to get the source from its repo, one needs to do this before:

```bash
$ git submodule init
$ git submodule update --remote
```

Since the actual simulator code used by the cluster contest script is the one packed in `contest.zip`, any changes, fixes, upgrades, extensions to the simulator have to be done outside and zipped it into `contest.zip` file again.

For example, if one modifies the code in `contest/`, a new `contest.zip` can be generated as follows:

```bash
$ rm -f contest.zip ; cd contest/ ; zip -r  ../contest.zip * ; cd ..
```

## TROUBLESHOOTING

- Cannot connect all hosts with message: _"Exception: Error reading SSH protocol banner"_
  - This happens when a single host has more than 10 CPUs.
  - The problem is not the script, but the ssh server in the cluster. By default it does not accept more than 10 connections.
  - Configure `/etc/ssh/sshd_config:` in the host with `MaxStartups 20:30:60`
  - Check [this issue](https://github.com/ssardina-teaching/pacman-contest/issues/26)

## SCREENSHOT

![Contest Result](extras/screenshot01.png)



## LICENSE

This project is using the GPLv3 for open source licensing for information and the license visit GNU website (<https://www.gnu.org/licenses/gpl-3.0.en.html>).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
