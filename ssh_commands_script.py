#!/usr/bin/python
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


def upload_files(run):
    today = datetime.date.today()
    os.chdir("results%s_%s_%s"%(today.year,today.month,today.day))    
    os.system("tar cvf recorded_games_%s_%s_%s.tar *recorded*  *replay*"%(today.year,today.month,today.day) )
    print "tar cvf recorded_games_%s_%s_%s.tar *recorded* *replay*"%(today.year,today.month,today.day) 
    os.chdir('..')
    os.system("tar cvf results%s_%s_%s.tar results%s_%s_%s/*"%(today.year,today.month,today.day,today.year,today.month,today.day) )

    #destination = "/run/user/1000/gvfs/smb-share\:server\=storage1.eng.unimelb.edu.au\,share\=mywebpages/comp90054tournament/"
    destination="www"
    
    print "tar cvf results%s_%s_%s.tar results%s_%s_%s/*"%(today.year,today.month,today.day,today.year,today.month,today.day)
    os.system("cp results%s_%s_%s.tar %s"%(today.year,today.month,today.day,destination))
    os.system( "tar xvf results%s_%s_%s.tar "%(today.year,today.month,today.day) )
    os.system( "rm  -rf %s/results%s_%s_%s"%(destination,today.year,today.month,today.day) )
    #os.system( "chmod 755  results%s_%s_%s/*"%(today.year,today.month,today.day) )
    #os.system( "chmod 755  results%s_%s_%s"%(today.year,today.month,today.day) )
    os.system( "mv results%s_%s_%s %s/results%s_%s_%s"%(today.year,today.month,today.day,destination,today.year,today.month,today.day) )
    
    output="<html><body><h1>Results Pacman Unimelb Tournament by Date</h1>"
    for root, dirs, files in os.walk(destination):
        for d in dirs:
            output+="<a href=\"http://people.eng.unimelb.edu.au/nlipovetzky/comp90054tournament/%s/results.html\"> %s  </a> <br>"%(d,d)
    output+="<br></body></html>"
    print "%s/results.html"%(destination)
    print output
    outstream = open("%s/results.html"%(destination),"w")
    outstream.writelines(output)
    outstream.close()

    #<a href="http://ww2.cs.mu.oz.au/482/tournament/layouts.tar.bz2"> Layouts used. Each day 2 new layouts are used  </a> <br>
    

    print "results%s_%s_%s.tar  Uploaded!"%(today.year,today.month,today.day)

if __name__ == '__main__':
    run = RunCommand()
    
    # parser = argparse.ArgumentParser()
    
    # parser.add_argument('--user',  help='username', nargs='?' )
    # parser.add_argument('--pass',  help='password', nargs='?' )
    # args = vars(parser.parse_args())


    '''
    ' ADD HOSTS
    '''
    username = 'nlipovetzky'
    password = ''
    run.do_add_host( "dimefox.eng.unimelb.edu.au,%s,%s"%(username,password) )

        
    run.do_connect()


    '''
    ' RUN THE COMMANDS HERE
    '''
    today = datetime.date.today()

    '''
    ' tar the submitted teams and download to local machine
    '''

    #CHANGE STORAGE2 FOR LOCAL     ###########run.do_run( "tar cvf teams%s_%s_%s.tar  /storage2/beta/users/nlipovetzky/test_teams/* "%(today.year,today.month,today.day) )
    
    # run.do_run( "tar cvf teams%s_%s_%s.tar  /local/submit/submit/COMP90054/2/* "%(today.year,today.month,today.day) )

    # run.do_get( "teams%s_%s_%s.tar"%(today.year,today.month,today.day) )    

    # os.system("rm -rf storage2/")
    # os.system("rm -rf local/")

    # os.system("tar xvf teams%s_%s_%s.tar"%(today.year,today.month,today.day) )
    
    '''
    ' unzip each team, copy it to teams folder, retrieve Teamname and AgentFactory from each config.py file, 
    ' and copy ff to each team folder
    '''
    teams = []
    os.system("rm -rf teams/")
    os.system("mkdir teams")
    #CHANGE STORAGE2 FOR LOCAL
    #for root, dirs, files in os.walk("storage2"):
    for root, dirs, files in os.walk("local"):
        for f in files:
            fullpath = os.path.join(root, f)
            if fullpath.split('/')[-1].find( ".zip" ) != -1 :
                os.system("cp -rf %s teams/."%(fullpath))
                print "cp -rf %s teams/."%(fullpath)
                os.system("unzip teams/%s -d teams/"%(f))
                print "unzip teams/%s -d teams/"%(f)
                os.system("rm teams/%s"%(f))
                print "rm teams/%s"%(f)                
                folder_name = f.split(".zip")[0]

                if os.path.isfile("teams/%s/ff"%(folder_name)) is False:
                    os.system("cp staffteam/ff teams/%s/."%(folder_name))
                    print "cp staffteam/ff teams/%s/."%(folder_name)                
 
                TeamName = fullpath.split('/')[-1].split('.')[0]               
                AgentFactory = 'teams/'+TeamName+'/team.py'

                print "teams/%s/team.py"%(TeamName)
                if os.path.isfile("teams/%s/team.py"%(TeamName)) is False:
                    print "team.py missing!"
                    exit(1)
                
                teams.append( (TeamName, AgentFactory) )



#uncomment to add staffteam in the competition
    teams.append( ("StaffTeam","teams/staffteam/team.py") )
    os.system("cp  -rf staffteam teams/.")
    os.system("rm -rf contest2016/teams/")
    os.system("cp  -rf teams contest2016/.")
    print "cp  -rf unimelb_tournament_scripts/teams contest2016/."

    '''
    ' Move to folder where pacman code is located (assume) is at '..'
    ' prepare the folder for the results, logs and the html
    '''

    
    print "\n\n", teams, "\n\n"



    os.system("rm -rf results%s_%s_%s"%(today.year,today.month,today.day))
    os.system("mkdir results%s_%s_%s"%(today.year,today.month,today.day))

    if len(teams) is 1:
          output = "<html><body><h1>Date Tournament %s/%s/%s <br> 0 Teams participated!!</h1>"%(today.year,today.month,today.day)
          output += "</body></html>"
          outstream = open("results%s_%s_%s/results.html"%(today.year,today.month,today.day),"w")
          outstream.writelines(output)
          outstream.close()
          print "results%s_%s_%s/results.html summary generated!"%(today.year,today.month,today.day)
          upload_files(run)

          run.do_close()
          exit(0)

    
    ladder = dict()
    games = []
    for n,a in teams:
        ladder[n]=[]


    errors = dict()
    for i in range(0,len(teams)):
        (n,a) = teams[i]
        errors[n]=0
    '''
    ' captureLayouts sets how many layouts are going to be used at the tournament
    ' steps is the length of each game
    ' the tournament plays each team twice against each other, once as red team, once as blue
    '''

    os.chdir('contest2016')

    print os.system('pwd')
    captureLayouts = 4
    steps = 1200
#    captureLayouts = 4
#    steps = 3000
    for i in range(0,len(teams)):
            for j in range(i+1,len(teams)):
                for g in xrange(1,captureLayouts):
                    for home in xrange(0,2):
                        hometeam = None
                        awayteam = None
                        if home == 0:
                            hometeam = teams[i]
                            awayteam = teams[j]
                        else:
                            hometeam = teams[j]
                            awayteam = teams[i]

                        (n1,a1) = hometeam
                        (n2,a2) = awayteam
                        print "game %s vs %s"%(n1, n2)
                        print "python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record"%(a1,a2,g,steps)
                        os.system("python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record > ../results%s_%s_%s/%s_vs_%s_contest1%dCapture_recorded.log"%(a1,a2,g,steps,today.year,today.month,today.day,n1,n2,g))
                        instream = open("../results%s_%s_%s/%s_vs_%s_contest1%dCapture_recorded.log"%(today.year,today.month,today.day,n1,n2,g),"r")
                        lines = instream.readlines()
                        instream.close()
                        score = 0
                        winner = None
                        looser = None
                        bug = False
                        for line in lines:
                            if line.find( "wins by" ) != -1:
                                score = abs(int(line.split('wins by')[1].split('points')[0]))
                                if line.find('Red') != -1: 
                                    winner = n1 
                                    looser = n2
                                elif line.find('Blue') != -1: 
                                    winner = n2
                                    looser = n1
                            if line.find( "The Blue team has returned at least " ) != -1:
                                score = abs(int(line.split('The Blue team has returned at least ')[1].split(' ')[0]))
                                winner = n2
                                looser = n1
                            elif line.find( "The Red team has returned at least " ) != -1:
                                score = abs(int(line.split('The Red team has returned at least ')[1].split(' ')[0]))
                                winner = n1
                                looser = n2
                            elif line.find( "Tie Game" ) != -1:
                                winner = None
                                looser = None
                            elif line.find( "agent crashed" ) != -1:
                                bug = True
                                if line.find( "Blue agent crashed" ) != -1:
                                    errors[n2]+=1
                                if line.find( "Red agent crashed" ) != -1:
                                    errors[n1]+=1

                        
                        if winner == None and bug is False:
                            ladder[n1].append(score)
                            ladder[n2].append(score)
                        elif bug is False:
                            ladder[winner].append(score)
                            ladder[looser].append(-1 * score)
                        
                        os.system("mv replay* ../results%s_%s_%s/%s_vs_%s_contest1%dCapture_replay"%(today.year,today.month,today.day,n1,n2,g))
                        if bug is False:
                            games.append( (n1,n2,"contest1%dCapture"%g,score,winner) )
                        else:
                            games.append( (n1,n2,"contest1%dCapture"%g,9999,winner) )
                            
    team_stats = dict()

    os.chdir('..')
    
    '''
    ' Compute ladder and create html with results
    '''
    for team, scores in ladder.iteritems():

        wins = 0
        draws = 0
        loses = 0
        sum_score = 0
        for s in scores:
            if s > 0:
                wins+=1
            elif s == 0:
                draws+=1
            else:
                loses+=1
            sum_score += s
        
        team_stats[team]=[((wins*3) + (draws) ),wins,draws,loses,errors[team],sum_score]
    
    output = "<html><body><h1>Date Tournament %s/%s/%s </h1><br><table border=\"1\">"%(today.year,today.month,today.day)
    output += "<tr><th>Team</th><th>Points</th><th>Win</th><th>Tie</th><th>Lost</th><th>FAILED</th><th>Score Balance</th></tr>"
    for key, (points,wins,draws,loses,errors,sum_score) in sorted(team_stats.items(), key=lambda (k, v): v[0], reverse=True):        
        output += "<tr><td align=\"center\">%s</td><td align=\"center\">%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\" >%d</td></tr>" % (key,points,wins,draws,loses,errors,sum_score )
    output += "</table>"

    output += "<br><br> <h2>Games</h2><br><a href=\"recorded_games_%s_%s_%s.tar\">DOWNLOAD RECORDED GAMES!</a><br><table border=\"1\">"%(today.year,today.month,today.day)
    output += "<tr><th>Team1</th><th>Team2</th><th>Layout</th><th>Score</th><th>Winner</th></tr>"
    for (n1,n2,layout,score,winner) in games:
        output += "<tr><td align=\"center\">"
        if winner == n1:            
            output +="<b>%s</b>"%n1
        else:
            output +="%s"%n1
        output +="</td><td align=\"center\">"
        if winner == n2:            
            output +="<b>%s</b>"%n2
        else:
            output +="%s"%n2
        if score == 9999:
            output +="</td><td align=\"center\">%s</td><td align=\"center\" >--</td><td align=\"center\"><b>FAILED</b></td></tr>"%(layout, )
        else:
            output +="</td><td align=\"center\">%s</td><td align=\"center\" >%d</td><td align=\"center\"><b>%s</b></td></tr>"%(layout,score,winner )

    output += "</table></body></html>"
    print "results%s_%s_%s/results.html summary generated!"%(today.year,today.month,today.day)

    outstream = open("results%s_%s_%s/results.html"%(today.year,today.month,today.day),"w")
    outstream.writelines(output)
    outstream.close()    

    '''
    ' upload files to server
    '''
    upload_files(run)

    run.do_close()
