# PACMAN CONQUER THE FLAG - CONTEST SUPPORT SCRIPT #

This script can be used to ran a Berkley Pacman Conquer the Flag Contest (http://ai.berkeley.edu/contest.html)

It was developed for RMIT COSC1125/1127 AI course in 2017 (lecturer A/Prof. Sebastian Sardina), based on an original script from Dr. Nir Lipovetzky.

CONTACT: Sebastian Sardina (ssardina@gmail.com)

### Pre-requisites ###

* Python >=2.7
* python-future

* Each teams is a .zip file; they should all go in a directory (e.g., teams/)



### Genearl description how the script works ###

1. The contest infrastructure used is stored in contest.zip and comes from contest/ If one wants to change anything from the contest scripts, 
one has to do the changes in contest/ and zip it up into contest.zip (without any dir inside).

2. The script will use contest.zip, layouts.zip (where some layouts are stored), and a set of teams, and build a contest_and_teams.zip file.

3. The contest_and_teams.zip file is then sent to the workers, expanded there, and executed. The log and replays are copied back.




