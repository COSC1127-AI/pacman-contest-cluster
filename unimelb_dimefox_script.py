#!/usr/bin/python
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


def upload_files(run, year, month, day):

    destination = "/run/user/1000/gvfs/smb-share\:server\=silo-hq1.eng.unimelb.edu.au\,share\=mywebpages/comp90054tournament"
    cwd = os.getcwd()        
    os.system("cp -rf www/* %s/."%destination)
    
    
    
    
if __name__ == '__main__':
    run = RunCommand()
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--username',  help='username', nargs='?' )
    parser.add_argument('--password',  help='password', nargs='?' )
    parser.add_argument('--cron-script-folder',  help='specify the folder to the scripts in order to run cron', nargs='?' )
    args = vars(parser.parse_args())



    '''
    ' TO RUN ON CRON
    '''
    if 'cron-script-folder' in args:
        os.chdir(args['cron-script-folder'])
    
    '''
    ' ADD HOSTS
    '''
    if 'username' or 'password' not in args:
        print "SPECIFY username and password: \n\tpython unimelb_dimefox_script.py --username xxxx --password xxxx "
        sys.exit(1)
        
    username = args['username']
    password = args['password']


    run.do_add_host( "dimefox.eng.unimelb.edu.au,%s,%s"%(username,password) )

        
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
    
    run.do_run( "tar cvf teams%s_%s_%s.tar  /local/submit/submit/COMP90054/2/* "%(year,month,day) )
    run.do_get( "teams%s_%s_%s.tar"%(year,month,day) )    
    os.system("rm -rf storage2/")
    os.system("rm -rf local/")
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

    os.system("python pacman-ssh-contest.py --compress-log --organizer UNIMELB  --teams-root teams/  --output-path www/  --max-steps 1200  --include-staff-team --no-fixed-layouts 2 --no-random-layouts 2  --ignore-file-name-format   --workers-file-path workers-unimelb.json")

    
    '''
    ' upload files to server
    '''
    
    upload_files(run, year, month, day)

    run.do_close()
