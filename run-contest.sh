#!/bin/bash
##########################
#
# run like <script> |& tee contest-day-`date +"%Y-%m-%d--%H-%M"`.txt

##### GET OPTIONS FROM COMMAND-LINE
NO_ARGS=$#   # Get the number of arguments passed in the command line
MY_NAME=${0##*/} 
DIR_SCRIPT=`dirname $0` # Find path of the current script

if [ "$NO_ARGS" != 4 ]; then
  printf "**** Script by Sebastian Sardina (2020) \n\n"
  printf "Script needs the number of splits, no of random layouts, and no of fixed layouts, and text description \n\n"
  printf "usage: ./$MY_NAME <no splits> <no random layouts> <no fixed layouts> <description>\n"
  exit
fi

################################
# VARIABLES TO CHANGE PER CASE
################################

# System variables
PYTHON=/usr/local/bin/python
TEE=/usr/bin/tee
NOW=`date +"%Y-%m-%d--%H-%M"`
# Script locations
DIR_CLONER=/mnt/ssardina-volume/cosc1125-1127-AI/git-hw-submissions.git/
DIR_CLUSTER=/mnt/ssardina-volume/cosc1125-1127-AI/AI22/contest/pacman-contest-cluster.git/
WORKERS_FILE=/mnt/ssardina-volume/cosc1125-1127-AI/AI22/contest/workers-nectar22.json

# Project variables
GH_ORG="RMIT-COSC1127-1125-AI22"
PREFIX_REPOS="contest"
TAG=testing
ROOT_PROJECT=/mnt/ssardina-volume/cosc1125-1127-AI/AI22/contest/preliminary
LOG_FILE="${ROOT_PROJECT}/contest-feedback-${NOW}.log"      # log of the contest
CONFIG_FILE=${ROOT_PROJECT}/config-feedback-${NOW}.json   # config file to save configuration
REPO_FILE=${ROOT_PROJECT}/repos.csv
TIMESTAMP_FILE=${ROOT_PROJECT}/timestamps.csv
SUBMISSIONS=${ROOT_PROJECT}/submissions
WWW=${ROOT_PROJECT}/www
STAFF_DIR=${ROOT_PROJECT}/reference-teams/

# Configuration of contest as per CLI options provided
SPLIT=$1
RANDOM_LAYOUTS=$2
FIXED_LAYOUTS=$3
DESCRIPTION="RMIT COSC1127/1125 AI'22 (Prof. Sebastian Sardina) - $4"
STEPS=1200


main_function() {
  # 1. get into the dir where this script is located!
  cd $DIR_SCRIPT

  # 2. Scrape all repos available (as they may be created at different times...)
  OPTIONS=( -u ssardina -t ~/.ssh/keys/gh-token-ssardina.txt $GH_ORG $PREFIX_REPOS $REPO_FILE )
  CMD=($PYTHON $DIR_CLONER/gh_classroom_collect.py ${OPTIONS[@]})
  echo "=================================================="
  echo ${CMD[@]} 
  echo "=================================================="
  ${CMD[@]}

  # 3. Clone the primary repos using the main tag (e.g., "test-submission")
  OPTIONS=( --file-timestamps $TIMESTAMP_FILE  $REPO_FILE $TAG $SUBMISSIONS )
  CMD=($PYTHON $DIR_CLONER/git_clone_submissions.py ${OPTIONS[@]})
  echo "=================================================="
  echo ${CMD[@]} 
  echo "=================================================="
  # $PYTHON $DIR_CLONER/git_clone_submissions.py "${OPTIONS[@]}"
  ${CMD[@]}
  
  # 3. Run a contest
  OPTIONS=( --organizer "$DESCRIPTION" 
    --teams-roots $SUBMISSIONS  
    --staff-teams-vs-others-only --staff-teams-roots $STAFF_DIR --hide-staff-teams     --www-dir $WWW  --workers-file $WORKERS_FILE
    --max-steps $STEPS 
    --no-fixed-layouts $FIXED_LAYOUTS --no-random-layouts $RANDOM_LAYOUTS   --build-config-file $CONFIG_FILE 
    --split $SPLIT 
    --score-thresholds 25 38 53 88 )
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
