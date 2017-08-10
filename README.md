# PACMAN CONQUER THE FLAG - CONTEST SUPPORT SCRIPT #

This script can be used to ran a Berkley Pacman Conquer the Flag Contest (http://ai.berkeley.edu/contest.html)

It was developed for RMIT COSC1125/1127 AI course in 2017 (lecturer A/Prof. Sebastian Sardina), based on an original script from Dr. Nir Lipovetzky.

CONTACT: Sebastian Sardina (ssardina@gmail.com)

### Pre-requisites ###

* Python >=2.7
* python-future

* Each teams is a .zip file; they should all go in a directory (e.g., teams/)



### General description how the script works ###

The mains components are:

- pacman-ssh-contest.py: main script
- cluster_manager.py: the script to manage clusters
- contest.zip: the actual main contest infrastructed, based on that one from UC (with minor fixes, e.g., delay in replays)
- layouts.zip: some interesting layouts that can be used (beyond the randomly generated ones)
- staff_team.zip: the team from the staff, used for --include-staff-team option
- contest/ subdir: developing place for contest.zip. The .zip file should contain all files in the root of the .zip

User needs to provide:

- Set of teams in some subdirectory, each in a .zip file (for option --teams)
- workers.json: listing the cluster setting to be used (for option --workers-file-path)
- teams-mapping.csv: a csv mapping submissions to teams (for option --team-names-file)

Process:

1. The script authenticate to all workers.

2. The script will use contest.zip, layouts.zip (where some layouts are stored), and a set of teams, and build a contest_and_teams.zip file.

2. File contest_and_teams.zip is transferred to the workers for each game, expanded there, and executed. The log and replays are copied back.




