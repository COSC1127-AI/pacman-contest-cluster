#!/usr/bin/python

#  ----------------------------------------------------------------------------------------------------------------------
# Import standard stuff

import os
import sys
import datetime
import argparse
import json

# ----------------------------------------------------------------------------------------------------------------------
# Verify all necessary packages are present

missing_packages = []
try:
    from getpass import getpass
except:
    missing_packages.append('getpass')

try:
    import paramiko
except:
    missing_packages.append('paramiko')

if missing_packages:
    print('Some packages are missing. Please, run `pip install %s`' % ' '.join(missing_packages))
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------
# Import class from helper module

from ssh_helper import RunCommand

# ----------------------------------------------------------------------------------------------------------------------
# Parse arguments

def load_settings():
    CONFIG_PATH = 'config.json'

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            settings = json.load(f)
    else:
        settings = {}

    parser = argparse.ArgumentParser(
        description='This script is to run a tournament between teams of agents for the Pacman package developed by '
                    'John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu) at UC Berkeley.\n'
                    '\n'
                    'After running the tournament, the script generates a report in HTML. The report is, optionally, '
                    'uploaded to a specified server via scp.\n'
                    '\n'
                    'The parameters are saved in config.json, so it is only necessary to pass them the first time or '
                    'if they have to be updated.')

    parser.add_argument(
        '--organizer',
        help='name of the organizer of the contest',
    )
    parser.add_argument(
        '--host',
        help='ssh host'
    )
    parser.add_argument(
        '--user',
        help='username'
    )
    parser.add_argument(
        '--output-path',
        help='output directory',
        default='www'
    )
    parser.add_argument(
        '--contest-code-name',
        help='output directory',
        default='contest_%s' % datetime.datetime.today().year
    )
    args = vars(parser.parse_args())

    if args.organizer:
        settings['organizer'] = args.organizer
    if args.organizer:
        settings['host'] = args.host
    if args.organizer:
        settings['user'] = args.user
    if args.organizer:
        settings['output_path'] = args.output_path
    if args.organizer:
        settings['contest_code_name'] = args.contest_code_name

    missing_parameters = {'organizer', 'host', 'user', 'output_path', 'contest_code_name'} - set(settings.keys())
    if missing_parameters:
        print('Missing parameters: %s. Aborting.' % list(sorted(missing_parameters)))
        parser.print_help()
        sys.exit(1)

    with open(CONFIG_PATH, 'w') as f:
        json.load(f, settings)

    return settings

# ----------------------------------------------------------------------------------------------------------------------

def upload_files(run, date_str, settings):
    os.chdir("results_%s" % date_str)
    os.system("tar cvf recorded_games_%s.tar *recorded*  *replay*" % date_str)
    print "tar cvf recorded_games_%s.tar *recorded* *replay*" % date_str
    os.chdir('..')
    os.system("tar cvf results_%s.tar results_%s/*" % (date_str, date_str))

    destination = "www"

    # TODO change to use Python functions so that this can run on non-Unix systems
    print "tar cvf results_%s.tar results_%s/*" % (
    date_str, date_str)
    os.system("cp results_%s.tar %s" % (date_str, destination))
    os.system("tar xvf results_%s.tar " % date_str)
    os.system("rm  -rf %s/results_%s" % (destination, date_str))
    # os.system( "chmod 755  results_%s/*"%(today.year,today.month,today.day) )
    # os.system( "chmod 755  results_%s"%(today.year,today.month,today.day) )
    os.system("mv results_%s %s/results_%s" % (date_str, destination, date_str))

    # TODO Parameterize this string
    output = "<html><body><h1>Results Pacman %s Tournament by Date</h1>" % settings['organizer']
    for root, dirs, files in os.walk(destination):
        for d in dirs:
            output += "<a href=\"%s/%s/results.html\"> %s  </a> <br>" % (settings['results_web_page'], d, d)
    output += "<br></body></html>"
    print "%s/results.html" % destination
    print output
    out_stream = open("%s/results.html" % destination, "w")
    out_stream.writelines(output)
    out_stream.close()

    # <a href="http://ww2.cs.mu.oz.au/482/tournament/layouts.tar.bz2"> Layouts used. Each day 2 new layouts are used  </a> <br>


    print "results_%s.tar  Uploaded!" % date_str


if __name__ == '__main__':
    settings = load_settings()

    run = RunCommand()

    '''
    ' ADD HOSTS
    '''
    run.do_add_host("%s,%s,%s" % (settings['host'], settings['user'], getpass()))

    run.do_connect()

    '''
    ' RUN THE COMMANDS HERE
    '''
    date_str = datetime.date.today().isoformat()

    '''
    ' tar the submitted teams and download to local machine
    '''

    # CHANGE STORAGE2 FOR LOCAL     ###########run.do_run( "tar cvf teams_%s.tar  /storage2/beta/users/nlipovetzky/test_teams/* "%(today.year,today.month,today.day) )

    # run.do_run( "tar cvf teams_%s.tar  /local/submit/submit/COMP90054/2/* "%(today.year,today.month,today.day) )

    # run.do_get( "teams_%s.tar"%(today.year,today.month,today.day) )

    # os.system("rm -rf storage2/")
    # os.system("rm -rf local/")

    # os.system("tar xvf teams_%s.tar"%(today.year,today.month,today.day) )

    '''
    ' unzip each team, copy it to teams folder, retrieve TeamName and AgentFactory from each config.py file, 
    ' and copy ff to each team folder
    '''
    teams = []
    os.system("rm -rf teams/")
    os.system("mkdir teams")
    # CHANGE STORAGE2 FOR LOCAL
    # for root, dirs, files in os.walk("storage2"):
    for root, dirs, files in os.walk("local"):
        for f in files:
            full_path = os.path.join(root, f)
            if full_path.split('/')[-1].find(".zip") != -1:
                os.system("cp -rf %s teams/." % full_path)
                print "cp -rf %s teams/." % full_path
                os.system("unzip teams/%s -d teams/" % f)
                print "unzip teams/%s -d teams/" % f
                os.system("rm teams/%s" % f)
                print "rm teams/%s" % f
                folder_name = f.split(".zip")[0]

                if os.path.isfile("teams/%s/ff" % folder_name) is False:
                    os.system("cp staff_team/ff teams/%s/." % folder_name)
                    print "cp staff_team/ff teams/%s/." % folder_name

                TeamName = full_path.split('/')[-1].split('.')[0]
                AgentFactory = 'teams/' + TeamName + '/team.py'

                print "teams/%s/team.py" % TeamName
                if os.path.isfile("teams/%s/team.py" % TeamName) is False:
                    print "team.py missing!"
                    exit(1)

                teams.append((TeamName, AgentFactory))



    # uncomment to add staff_team in the competition
    teams.append(("staff_team", "teams/staff_team/team.py"))
    os.system("cp  -rf staff_team teams/.")
    os.system("rm -rf %s/teams/" % settings['contest_code_name'])
    os.system("cp  -rf teams %s/." % settings['contest_code_name'])
    print "cp  -rf %s_tournament_scripts/teams %s/." % (settings['organizer'], settings['contest_code_name'])

    '''
    ' Move to folder where pacman code is located (assume) is at '..'
    ' prepare the folder for the results, logs and the html
    '''

    print "\n\n", teams, "\n\n"

    os.system("rm -rf results_%s" % date_str)
    os.system("mkdir results_%s" % date_str)

    if len(teams) is 1:
        output = "<html><body><h1>Date Tournament %s/%s/%s <br> 0 Teams participated!!</h1>" % (
        date_str)
        output += "</body></html>"
        out_stream = open("results_%s/results.html" % date_str, "w")
        out_stream.writelines(output)
        out_stream.close()
        print "results_%s/results.html summary generated!" % date_str
        upload_files(run, date_str, settings)

        run.do_close()
        exit(0)

    ladder = dict()
    games = []
    for n, a in teams:
        ladder[n] = []

    errors = dict()
    for i in range(0, len(teams)):
        (n, a) = teams[i]
        errors[n] = 0
    '''
    ' captureLayouts sets how many layouts are going to be used at the tournament
    ' steps is the length of each game
    ' the tournament plays each team twice against each other, once as red team, once as blue
    '''

    # TODO parameterize this (and all other instances of this string)
    os.chdir(settings['contest_code_name'])

    print os.system('pwd')
    captureLayouts = 4
    steps = 1200
    #    captureLayouts = 4
    #    steps = 3000
    for i in range(0, len(teams)):
        for j in range(i + 1, len(teams)):
            for g in xrange(1, captureLayouts):
                for home in xrange(0, 2):
                    home_team = None
                    away_team = None
                    if home == 0:
                        home_team = teams[i]
                        away_team = teams[j]
                    else:
                        home_team = teams[j]
                        away_team = teams[i]

                    (n1, a1) = home_team
                    (n2, a2) = away_team
                    print "game %s vs %s" % (n1, n2)
                    print "python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record" % (a1, a2, g, steps)
                    os.system(
                        "python capture.py -r %s -b %s -l contest1%dCapture -i %d -q --record > ../results_%s/%s_vs_%s_contest1%dCapture_recorded.log" % (
                        a1, a2, g, steps, date_str, n1, n2, g))
                    in_stream = open("../results_%s/%s_vs_%s_contest1%dCapture_recorded.log" % (
                    date_str, n1, n2, g), "r")
                    lines = in_stream.readlines()
                    in_stream.close()
                    score = 0
                    winner = None
                    looser = None
                    bug = False
                    for line in lines:
                        if line.find("wins by") != -1:
                            score = abs(int(line.split('wins by')[1].split('points')[0]))
                            if line.find('Red') != -1:
                                winner = n1
                                looser = n2
                            elif line.find('Blue') != -1:
                                winner = n2
                                looser = n1
                        if line.find("The Blue team has returned at least ") != -1:
                            score = abs(int(line.split('The Blue team has returned at least ')[1].split(' ')[0]))
                            winner = n2
                            looser = n1
                        elif line.find("The Red team has returned at least ") != -1:
                            score = abs(int(line.split('The Red team has returned at least ')[1].split(' ')[0]))
                            winner = n1
                            looser = n2
                        elif line.find("Tie Game") != -1:
                            winner = None
                            looser = None
                        elif line.find("agent crashed") != -1:
                            bug = True
                            if line.find("Blue agent crashed") != -1:
                                errors[n2] += 1
                            if line.find("Red agent crashed") != -1:
                                errors[n1] += 1

                    if winner is None and bug is False:
                        ladder[n1].append(score)
                        ladder[n2].append(score)
                    elif bug is False:
                        ladder[winner].append(score)
                        ladder[looser].append(-1 * score)

                    os.system("mv replay* ../results_%s/%s_vs_%s_contest1%dCapture_replay" % (
                    date_str, n1, n2, g))
                    if bug is False:
                        games.append((n1, n2, "contest1%dCapture" % g, score, winner))
                    else:
                        games.append((n1, n2, "contest1%dCapture" % g, 9999, winner))

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
                wins += 1
            elif s == 0:
                draws += 1
            else:
                loses += 1
            sum_score += s

        team_stats[team] = [((wins * 3) + draws), wins, draws, loses, errors[team], sum_score]

    output = "<html><body><h1>Date Tournament %s/%s/%s </h1><br><table border=\"1\">" % (
    date_str)
    output += "<tr><th>Team</th><th>Points</th><th>Win</th><th>Tie</th><th>Lost</th><th>FAILED</th><th>Score Balance</th></tr>"
    for key, (points, wins, draws, loses, errors, sum_score) in sorted(team_stats.items(), key=lambda (k, v): v[0],
                                                                       reverse=True):
        output += "<tr><td align=\"center\">%s</td><td align=\"center\">%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\">%d</td><td align=\"center\" >%d</td><td align=\"center\" >%d</td></tr>" % (
        key, points, wins, draws, loses, errors, sum_score)
    output += "</table>"

    output += "<br><br> <h2>Games</h2><br><a href=\"recorded_games_%s.tar\">DOWNLOAD RECORDED GAMES!</a><br><table border=\"1\">" % (
    date_str)
    output += "<tr><th>Team1</th><th>Team2</th><th>Layout</th><th>Score</th><th>Winner</th></tr>"
    for (n1, n2, layout, score, winner) in games:
        output += "<tr><td align=\"center\">"
        if winner == n1:
            output += "<b>%s</b>" % n1
        else:
            output += "%s" % n1
        output += "</td><td align=\"center\">"
        if winner == n2:
            output += "<b>%s</b>" % n2
        else:
            output += "%s" % n2
        if score == 9999:
            output += "</td><td align=\"center\">%s</td><td align=\"center\" >--</td><td align=\"center\"><b>FAILED</b></td></tr>" % (
            layout,)
        else:
            output += "</td><td align=\"center\">%s</td><td align=\"center\" >%d</td><td align=\"center\"><b>%s</b></td></tr>" % (
            layout, score, winner)

    output += "</table></body></html>"
    print "results_%s/results.html summary generated!" % date_str

    out_stream = open("results_%s/results.html" % date_str, "w")
    out_stream.writelines(output)
    out_stream.close()

    '''
    ' upload files to server
    '''
    upload_files(run, date_str, settings)

    run.do_close()
