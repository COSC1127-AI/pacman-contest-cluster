#!/bin/bash
#
# This script deletes all logs from a team in a tmp contest folder
# This is used to then resume the contest and re-run all gmaes of that team

##### GET OPTIONS FROM COMMAND-LINE
NO_ARGS=$#   # Get the number of arguments passed in the command line
MY_NAME=${0##*/} 
if [ "$NO_ARGS" != 2 ]; then
	printf "**** Script by Sebastian Sardina (2020) \n\n"
	printf "usage: ./$MY_NAME <contest tmp folder> <team name>\n"
	exit
fi


##### SCRIPT STARTS HERE
CONTEST_DIR=$1
TEAM=$2


echo "I will delete all logs of team $TEAM in contest $1"
find "$CONTEST_DIR/" -name \*$TEAM*.log

## CHECK THE USER TO CONTINUE 
read -p "ARE YOU SURE YOU WANT TO DELETE ALL THIS FILES FROM CONTEST $CONTEST_DIR/? " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
	echo "Aborting..."
	exit 1
fi

find "$CONTEST_DIR/" -name \*$TEAM*.log -exec rm -f {} \;
