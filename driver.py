#!/usr/bin/python
import json
import sys
import os
import paramiko
import argparse
import datetime
from scp import SCPClient

import subprocess
import re
import shutil
import csv
import logging
import traceback
import time
# https://gitpython.readthedocs.io/en/2.1.9/reference.html
# http://gitpython.readthedocs.io/en/stable/tutorial.html
import git


"""
A Class to manage assignment submissions via git repositories.

Class takes a csv file containing repo URL GIT  for each team and a tag and will clone/update them in an
output directory.

It also produces a file submission_timestamp.csv with all timestamp of the tag for the successful repo cloned/updated.
"""
class GitSubmissions():

    def __init__(self, username, password):
        self.use_git_ssh = False
        self.min_teams_for_competition = 1
        self.competition_is_on = False
        self.add_timestamps = True
        self.submission_tag = 'submission-contest'
        self.output_folder = 'git-teams'
        self.DATE_FORMAT = '%-d/%-m/%Y %-H:%-M:%-S'  # (Australia)
        self.timestamps_file = 'submission_logs/submissions_timestamps_{}.csv'.format(time.strftime('%-d_%-m_%Y_%-H_%-M_%-S', time.localtime() ))
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%a, %d %b %Y %H:%M:%S')
        self.logging = logging.getLogger()
        self.username = username
        self.password = password

        
    def clone_repos( self, team_csv_file ):
        
        teams_file = open(team_csv_file, 'r')
        # Get the list of teams with their GIT URL from csv file
        teams_reader = csv.DictReader(teams_file, delimiter=',')
        list_teams = list(teams_reader)

        # # If there was a specific team given, just keep that one in the list to clone just that
        # if not args.team is None:
        #     list_teams = [team for team in list_teams if team['TEAM'] == args.team]


        # If a submission csv file exists, make a backup of it as it will be overwritten
        if os.path.exists(self.timestamps_file):
            shutil.copy(self.timestamps_file, self.timestamps_file + '.bak')

        # Open the submission file for writing
        if self.add_timestamps:
            submission_timestamps_file = open(self.timestamps_file, 'a')
            submission_writer = csv.DictWriter(submission_timestamps_file,
                                               fieldnames=['team', 'submitted_at', 'commit', 'tagged_at'])
        else:
            submission_timestamps_file = open(self.timestamps_file, 'w')
            submission_writer = csv.DictWriter(submission_timestamps_file,
                                               fieldnames=['team', 'submitted_at', 'commit', 'tagged_at'])
            submission_writer.writeheader()


        no_teams = len(list_teams)
        list_teams.sort(key=lambda tup: tup['TEAM'].lower())    # sort the list of teams
        self.logging.info('Database contains {} teams to clone in folder {}/.'.format(no_teams, self.output_folder))
        team_new = []
        team_missing = []
        team_unchanged = []
        team_updated = []
        team_names_set = set()
        for c, row in enumerate(list_teams, 1):
            print('\n')
            self.logging.info('Processing {}/{} team **{}** in git url {}.'.format(c, no_teams, row['TEAM'], row['GitLab HTTPS repository link']))

            #Remove spaces and strip bad characters
            team_name = row['TEAM'].replace(' ', '-').rstrip()
            re.sub(r'\W+', '',team_name)

            #Check if the name exists, if so, add the student numbers
            if team_name in team_names_set:
                team_name = "{}-{}-{}-{}".format(team_name,row['Student number of member 1'],row['Student number of member 2'],row['Student number of member 3'])
                if row['Student number of member 4 (if any)'] != '':
                    team_name = "{}-{}".format(team_name,row['Student number of member 4 (if any)'])

            team_names_set.add(team_name)
                        
            
            git_url = row['GitLab SSH repository link']
            if self.use_git_ssh is False:
                if self.username is not None:
                    git_url_rebase = row['GitLab HTTPS repository link'].split('://')
                    git_url = "{}://{}:{}@{}".format(git_url_rebase[0],self.username,self.password,git_url_rebase[1])
                    #If students forgot to enter .git at the end of the address, just append it.
                    if git_url.endswith(".git") is False:
                        git_url+=".git"
                else:
                    git_url = row['GitLab repository link']
                   
                
            git_local_dir = os.path.join(self.output_folder, team_name)

            #time.sleep(1) # Time in seconds.
            if not os.path.exists(git_local_dir):   # if there is already a local repo for the team
                print('\t Trying to clone NEW team repo from URL {}.'.format(git_url))
                try:
                    repo = git.Repo.clone_from(git_url, git_local_dir, branch=self.submission_tag)
                except git.GitCommandError as e:
                    team_missing.append(team_name)
                    self.logging.warning('Repo for team {} with tag {} cannot be cloned: {}'.
                                    format(team_name, self.submission_tag, e.stderr))
                    continue
                except KeyboardInterrupt:
                    self.logging.warning('Script terminated via Keyboard Interrupt; finishing...')
                    sys.exit("keyboard interrupted!")
                    
                submission_time, submission_commit, tagged_time = self.get_tag_time(repo, self.submission_tag)

                if submission_commit is None:
                    team_missing.append(team_name)                    
                    print('\t\t Team {} is Missing the tag {}.'.format(team_name, self.submission_tag))
                else:
                    print('\t\t Team {} cloned successfully with tag date {}.'.format(team_name, submission_time))
                    team_new.append(team_name)
            else:   # OK, so there is already a directory for this team in local repo, check if there is an update
                try:
                    # First get the timestamp of the local repository for the team
                    repo = git.Repo(git_local_dir)
                    submission_time_local, _, _ = self.get_tag_time(repo, self.submission_tag)
                    if submission_time_local is None:
                        print('\t No tag {} in the repository, strange as it was already there...'.format(self.submission_tag))
                    else:
                        print('\t Existing LOCAL submission for {} dated {}; updating it...'.format(team_name, submission_time_local))


                    # Next, update the repo to check if there is a new updated submission time for submission tag
                    repo.remote('origin').fetch(tags=True)
                    submission_time, submission_commit, tagged_time = self.get_tag_time(repo, self.submission_tag)
                    if submission_time is None: # self.submission_tag has been deleted! remove local repo, no more submission
                        team_missing.append(team_name)
                        print('\t No tag {} in the repository for team {} anymore; removing it...'.format(self.submission_tag,
                                                                                                          team_name))
                        shutil.rmtree(git_local_dir)
                        continue

                    # Checkout the repo from server (doesn't matter if there is no update, will stay as is)
                    repo.git.checkout(self.submission_tag)

                    # Now processs timestamp to report new or unchanged repo
                    if submission_time == submission_time_local:
                        print('\t\t Team {} submission has not changed.'.format(team_name))
                        team_unchanged.append(team_name)
                    else:
                        print('\t Team {} updated successfully with new tag date {}'.format(team_name, submission_time))
                        team_updated.append(team_name)
                except git.GitCommandError as e:
                        team_missing.append(team_name)
                        self.logging.warning('\t Problem with existing repo for team {}; removing it: {}'.format(team_name, e.stderr))
                        print('\n')
                        shutil.rmtree(git_local_dir)
                        continue
                except KeyboardInterrupt:
                        self.logging.warning('Script terminated via Keyboard Interrupt; finishing...')
                        sys.exit(1)
                except:
                        team_missing.append(team_name)
                        self.logging.warning('\t Local repo {} is problematic; removing it...'.format(git_local_dir))
                        print(traceback.print_exc())
                        print('\n')
                        shutil.rmtree(git_local_dir)
                        continue
            # Finally, write team into submission timestamp file
            submission_writer.writerow(
                {'team': team_name, 'submitted_at': submission_time, 'commit': submission_commit, 'tagged_at': tagged_time})

                        # local copy already exists - needs to update it maybe tag is newer

        print("\n ============================================== \n")
        print('NEW TEAMS: {}'.format(len(team_new)))
        for t in team_new:
            print("\t {}".format(t))
        print('UPDATED TEAMS: {}'.format(len(team_updated)))
        for t in team_updated:
            print("\t {}".format(t))
        print('UNCHANGED TEAMS: {}'.format(len(team_unchanged)))
        for t in team_unchanged:
            print("\t {}".format(t))
        print('TEAMS MISSING (or not clonned successfully): ({})'.format(len(team_missing)))
        for t in team_missing:
            print("\t {}".format(t))
        print("\n ============================================== \n")

        available_teams = len(team_new)+len(team_updated)+len(team_unchanged)
        print("\n ============================================== \n")
        print('TEAMS AVAILABLE TO COMPETE: {}'.format( available_teams ))
        if available_teams >= self.min_teams_for_competition :
            self.competition_is_on = True
        
    # Extract the timestamp for a given tag in a repo
    def get_tag_time(self, repo, tag_str):
        tag = next((tag for tag in repo.tags if tag.name == tag_str), None)

        # tag_commit = next((tag.commit for tag in repo.tags if tag.name == tag_str), None)        
        if tag is None:
            return None,None,None
        else:
            tag_commit = tag.commit
            tag_commit_date = time.localtime(tag_commit.committed_date)
            try:
                tagged_date = time.localtime(tag.object.tagged_date)    # if it is an annotated tag
            except:
                tagged_date = tag_commit_date   # if it is a lightweight tag
            return time.strftime(self.DATE_FORMAT, tag_commit_date), tag_commit, time.strftime(self.DATE_FORMAT, tagged_date)

    # return timestamps form a csv submission file
    def load_timestamps(self, timestamp_filename):
        team_timestamps = {}

        with open(timestamp_filename, 'r') as f:
            reader = csv.DictReader(f, delimiter=',', quotechar='"', fieldnames=['team', 'submitted_at', 'commit'])

            next(reader)    # skip header
            for row in reader:
                team_timestamps[row['team']] = row['submitted_at']
        return team_timestamps

"""
A Class to manage ssh connections to download submissions
"""
class RunCommand():

    def __init__(self):
        self.hosts = []
        
        self.connections = []

    def do_add_host(self, args):
        """add_host 
        Add the host to the host list"""
        if args:
            self.hosts.append(args.split(','))
        else:
            print ("usage: host ")

    def do_connect(self):
        """Connect to all hosts in the hosts list"""
        for host in self.hosts:            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
            client.connect(host[0], 
                username=host[1], 
                password=host[2])
            self.connections.append(client)

    def do_run(self, command):
        """run 
        Execute this command on all hosts in the list"""
        if command:
            for host, conn in zip(self.hosts, self.connections):
                print ('host: %s: %s' % (host[0], command))
                stdin, stdout, stderr = conn.exec_command(command)
                stdin.close()
                for line in stdout.read().split("\n"):
                    print ('host: %s: %s' % (host[0], line))
        else:
            print ("usage: run ")

    def do_close(self):
        for conn in self.connections:
            conn.close()

    def do_get( self, filename):
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())                  
            scp.get(filename)
            print ('get %s file from host: %s:' % (filename, host[0]))

    def do_put( self, filename, dest):
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())                  
            scp.put(filename,dest)
            print ('put %s file from host: %s:' % (filename, host[0]))


def upload_files( dest_www, year, month, day):
    
    cwd = os.getcwd()        
    os.system("cp -rf www/* %s/."%dest_www)
    
    
    
    
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    
    parser.add_argument('--dest-www',  help='Destination folder to publish www data in a web server. (it is recommended to map a web-server folder using smb)', nargs='?' )

    server_group = parser.add_argument_group('Download submission from a server using ssh connections', 'Submission options')
    server_group.add_argument('--username',  help='username for --teams-server-url or for https git connection', nargs='?' )
    server_group.add_argument('--password',  help='password for --teams-server-url or for https git connection', nargs='?' )
    server_group.add_argument('--teams-server-folder',  help='folder containing all the teams submitted at the server specified at --teams-server-name', nargs='?' )
    server_group.add_argument('--teams-server-url',  help='server address containing the teams submitted', nargs='?' )

    git_group = parser.add_argument_group('Download submission from GIT repos', 'Submission options')    
    git_group.add_argument('--teams-git-csv',  help='CSV containining columns TEAM and \'GitLab SSH repository link\' ', nargs='?' )
    
    parser.add_argument('--tournament-cmd',  help='specify all the options to run pacman-ssh-contesy.py', nargs='?' )
    
    parser.add_argument('--cron-script-folder',  help='specify the folder to the scripts in order to run cron', nargs='?' )

    #parser.add_argument('--driver-settings-json',  help='Specify all settings above in driver-settings.json', nargs='?' )
    
    args = vars(parser.parse_args())

    #with open(args['driver_settings_json'], 'r') as f:
    #    driver_details = json.load(f)['settings']

    #print driver_details


    '''
    ' TO RUN ON CRON
    '''
    if 'cron_script_folder' in args:
        os.chdir(args['cron_script_folder'])
        os.system('pwd')
    
    
    '''
    ' ADD HOSTS
    '''
    if ('username' or 'password' or 'teams_server_url' or 'teams_server_folder') not in args and ('teams_git_csv' not in args):
        print ("SPECIFY all this parameters to get submissions using ssh connection: \n\tpython driver.py --username xxxx --password xxxx --teams-server-url xxx --teams-server-folder xxx --tournament-cmd xxx  \nType --help option for more info\n")
        print ("or SPECIFY a csv file to clone the GIT repos: \n\tpython driver.py  --teams-git-csv xxx --tournament-cmd xxx  \nType --help option for more info\n")
        print (args)
        
        sys.exit(1)

    if 'teams_git_csv' in args:

        username = args['username']
        password = args['password']
        
        git_run = GitSubmissions( username, password )
        
        git_run.clone_repos( args['teams_git_csv'] )
        
        
        '''
        ' Retrieve all the zip files, copy them into teams folder
        '''

        os.system("rm -rf teams/")
        os.system("mkdir teams")

        top_pathlen = len(git_run.output_folder) + len(os.path.sep)
        for root, dirs, files in os.walk(git_run.output_folder):
            for d in dirs:

                #limit depth dir tree to 1
                if len(root[len(git_run.output_folder)+1:])  > 0:
                    continue
                
                fullpath = os.path.join(root, d)

                '''
                ' Rename directories with spaces
                '''
                fullpathclean = fullpath.replace(' ', '-')
                dclean = d.replace(' ', '-')
                if ' ' in fullpath:
                    fullpathslash = fullpath.replace(' ', '\ ')
                    os.system("mv %s %s"%(fullpathslash,fullpathclean))
                    print( "mv %s %s"%(fullpathslash,fullpathclean))

                retval = os.getcwd()
                if os.path.isdir('{}/pacman-contest/'.format(fullpathclean)) is False:
                    fullpathclean+='/comp90054-pacman'
                if os.path.isdir('{}/pacman-contest/'.format(fullpathclean)) is False:
                    print('Incorrect folder structure {}. Cannot find submission folder'.format(fullpathclean))
                    continue
                os.chdir('{}/pacman-contest/'.format(fullpathclean))
                print('cd {}/pacman-contest/'.format(fullpathclean))
                os.system('zip -r {}/{}.zip *'.format(retval,fullpathclean))
                os.chdir(retval)
                print('cd {}'.format(retval))
                print('zip -r {}/{}.zip *'.format(retval,fullpathclean))
                os.system("mv {}.zip teams/.".format(fullpathclean))
                print ("mv {}.zip teams/.".format(fullpathclean))

        if git_run.competition_is_on is False:
            print("\n NOT ENOUGH TEAMS TO COMPETE!!\n")
            sys.exit(1)
        
    else:

        username = args['username']
        password = args['password'] 

        teams_server_url = args['teams_server_url']
        teams_server_folder = args['teams_server_folder']

     
        run = RunCommand()        

        run.do_add_host( "%s,%s,%s"%(teams_server_url,username,password) )


        run.do_connect()


        '''
        ' RUN THE COMMANDS HERE
        '''
        today = datetime.date.today()
        year = today.year
        month = today.month
        day = today.day

        #This line makes sure that the we do not include old submissions
        os.system("rm -rf .%s"%teams_server_folder)
        print("rm -rf .%s"%teams_server_folder)


        '''
        ' tar submitted teams from server and download to local machine
        '''


        run.do_run( "tar cvf teams%s_%s_%s.tar  %s* "%(year,month,day,teams_server_folder) )
        run.do_get( "teams%s_%s_%s.tar"%(year,month,day) )
        
        run.do_close()

        os.system("tar xvf teams%s_%s_%s.tar"%(year,month,day) )


        '''
        ' Retrieve all the zip files, copy them into teams folder
        '''

        os.system("rm -rf teams/")
        os.system("mkdir teams")
        for root, dirs, files in os.walk("local"):
            for f in files:
                fullpath = os.path.join(root, f)
                if fullpath.split('/')[-1].find( ".zip" ) != -1 :
                    '''
                    ' Rename filenames with spaces
                    '''
                    fullpathclean = fullpath.replace(' ', '-')
                    if ' ' in fullpath:
                        fullpathslash = fullpath.replace(' ', '\ ')
                        os.system("mv %s %s"%(fullpathslash,fullpathclean))
                        print ("mv %s %s"%(fullpathslash,fullpathclean))

                    os.system("cp -rf %s teams/."%(fullpathclean))
                    print ("cp -rf %s teams/."%(fullpathclean))


    '''
    ' Run Competition Script
    '''
    tournament_cmd = args['tournament_cmd']
    dest_www = 'dest-www'
    if 'dest_www' in args:
        dest_www = args['dest_www']
        
    today = datetime.date.today()
    year = today.year
    month = today.month
    day = today.day

        
    print ("RUNNING: python pacman-ssh-contest.py %s"%(tournament_cmd))
    os.system("python3 pacman-ssh-contest.py %s"%(tournament_cmd))

    
    '''
    ' upload files to server
    '''
    
    upload_files( dest_www, year, month, day)
