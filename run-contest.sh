#!/bin/bash
##########################
#
# run like <script> |& tee contest-day-`date +"%Y-%m-%d--%H-%M"`.txt

##### GET OPTIONS FROM COMMAND-LINE
NO_ARGS=$#   # Get the number of arguments passed in the command line
MY_NAME=${0##*/} 

if [ "$NO_ARGS" != 4 ]; then
  printf "**** Script by Sebastian Sardina (2020) \n\n"
  printf "Script needs the number of splits, no of random layouts, and no of fixed layouts, and text description \n\n"
  printf "usage: ./$MY_NAME <no splits> <no random layouts> <no fixed layouts> <description>\n"
  exit
fi

DIR_SCRIPT=`dirname $0` # Find path of the current script
NOW=`date +"%Y-%m-%d--%H-%M"`
LOG_FILE="${DIR_SCRIPT}/contest-feedback-${NOW}.log"
PYTHON=/usr/local/bin/python
TEE=/usr/bin/tee


################################
# VARIABLES TO CHANGE PER CASE
################################

# Script locations
DIR_CLONER=/mnt/ssardina-volume/cosc1125-1127-AI/git-hw-submissions.git/
DIR_CLUSTER=/mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/pacman-contest-cluster.git/

# Options to the scripts
REPO_FILE=pc-repos.csv
TAG=testing
TIMESTAMP_FILE=pc-timestamps.csv
SUBMISSIONS=submissions
WORKERS_FILE=/mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/workers-nectar21.json
CONFIG_FILE=config-feedback.json    # config file to save configuration
WWW=/mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/preliminary/www
STAFF_DIR=/mnt/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/reference-contest/reference-teams

# Configuration of contest
SPLIT=$1
RANDOM_LAYOUTS=$2
FIXED_LAYOUTS=$3

#RANDOM_LAYOUTS=3
#FIXED_LAYOUTS=2

DESCRIPTION="RMIT COSC1127/1125 AI'21 (Prof. Sebastian Sardina) - $4"
STEPS=1200


main_function() {
  # First, get into the dir where this script is located!
  cd $DIR_SCRIPT

  # Clone the primary repos using the main tag (e.g., "test-submission")
  OPTIONS=( --file-timestamps $TIMESTAMP_FILE  $REPO_FILE $TAG $SUBMISSIONS )
  CMD=($PYTHON $DIR_CLONER/git_clone_submissions.py ${OPTIONS[@]})
  echo "=================================================="
  echo ${CMD[@]} 
  echo "=================================================="
  # $PYTHON $DIR_CLONER/git_clone_submissions.py "${OPTIONS[@]}"
  ${CMD[@]}
  
  # Build options to run contest
  OPTIONS=( --organizer "$DESCRIPTION" --teams-roots $SUBMISSIONS  --www-dir $WWW  --max-steps $STEPS  --no-fixed-layouts $FIXED_LAYOUTS --no-random-layouts $RANDOM_LAYOUTS  --workers-file $WORKERS_FILE --build-config-file $CONFIG_FILE --split $SPLIT --staff-teams-roots $STAFF_DIR  --hide-staff-teams --score-thresholds 25 38 53 88 )
  CMD=($PYTHON $DIR_CLUSTER/pacman_contest_cluster.py "${OPTIONS[@]}")
  echo "=================================================="
  echo ${CMD[@]} 
  echo "=================================================="
  # $PYTHON $DIR_CLUSTER/pacman_contest_cluster.py "${OPTIONS[@]}" 
  "${CMD[@]}"
}

if [ -z $TERM ]; then
  # if not run via terminal, log everything into a log file
  touch tea
  main_function 2>&1 >> $LOG_FILE
else
  # run via terminal, only output to screen
  main_function |& $TEE $LOG_FILE
fi
