#!/usr/bin/python
import json
import sys
import os
import paramiko
import argparse
import datetime
from scp import SCPClient

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
            print "usage: host "

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
                print 'host: %s: %s' % (host[0], command)
                stdin, stdout, stderr = conn.exec_command(command)
                stdin.close()
                for line in stdout.read().split("\n"):
                    print 'host: %s: %s' % (host[0], line)
        else:
            print "usage: run "

    def do_close(self):
        for conn in self.connections:
            conn.close()

    def do_get( self, filename):
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())                  
            scp.get(filename)
            print 'get %s file from host: %s:' % (filename, host[0])

    def do_put( self, filename, dest):
        for host, conn in zip(self.hosts, self.connections):
            scp = SCPClient(conn.get_transport())                  
            scp.put(filename,dest)
            print 'put %s file from host: %s:' % (filename, host[0])


def upload_files(run, dest_www, year, month, day):
    
    cwd = os.getcwd()        
    os.system("cp -rf www/* %s/."%dest_www)
    
    
    
    
if __name__ == '__main__':
    run = RunCommand()
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--username',  help='username for --teams-server-url', nargs='?' )
    parser.add_argument('--password',  help='password for --teams-server-url', nargs='?' )

    parser.add_argument('--dest-www',  help='Destination folder to publish www data in a web server. (it is recommended to map a web-server folder using smb)', nargs='?' )        
    parser.add_argument('--teams-server-folder',  help='folder containing all the teams submitted at the server specified at --teams-server-name', nargs='?' )
    parser.add_argument('--teams-server-url',  help='server address containing the teams submitted', nargs='?' )
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
    if 'cron-script-folder' in args:
        os.chdir(args['cron-script-folder'])
    
    '''
    ' ADD HOSTS
    '''
    if ('username' or 'password' or 'teams_server_url' or 'teams_server_folder') not in args:
        print "SPECIFY all this parameters: \n\tpython unimelb_dimefox_script.py --username xxxx --password xxxx --team-server-url xxx --team-server-folder xxx --tournament-cmd xxx  \nType --help option for more info\n"
        print args
        
        sys.exit(1)
        
    username = args['username']
    password = args['password'] 

    teams_server_url = args['teams_server_url']
    teams_server_folder = args['teams_server_folder']
    tournament_cmd = args['tournament_cmd']
    
    dest_www = 'dest-www'
    if 'dest_www' in args:
        dest_www = args['dest_www']

    


    run.do_add_host( "%s,%s,%s"%(teams_server_url,username,password) )

        
    run.do_connect()


    '''
    ' RUN THE COMMANDS HERE
    '''
    today = datetime.date.today()
    year = today.year
    month = today.month
    day = today.day

    '''
    ' tar submitted teams from server and download to local machine
    '''
    
    run.do_run( "tar cvf teams%s_%s_%s.tar  %s* "%(year,month,day,teams_server_folder) )
    run.do_get( "teams%s_%s_%s.tar"%(year,month,day) )    
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
                os.system("cp -rf %s teams/."%(fullpath))
                print "cp -rf %s teams/."%(fullpath)


    '''
    ' Run Competition Script
    '''

    print "RUNNING: python pacman-ssh-contest.py %s"%(tournament_cmd)
    os.system("python pacman-ssh-contest.py %s"%(tournament_cmd))

    
    '''
    ' upload files to server
    '''
    
    upload_files(run, dest_www, year, month, day)

    run.do_close()
