
import tarfile
import shutil
import os
import json  
from datetime import datetime
import re

DATA_URL = '/home/nirlipo/contest-2020/www'

def main():
    json_files = sorted([f for f in os.listdir(f'{DATA_URL}/stats-archive/') if os.path.isfile(os.path.join(DATA_URL,'stats-archive', f))], reverse=True)

    print(f'{DATA_URL}/stats-archive/')
    print(json_files)
    for fname in json_files:
        with open(f'{DATA_URL}/stats-archive/{fname}') as f: 
            d = json.load(f) 

        teams = d['team_stats'].keys()
        print(fname)
        match = re.search('stats_(.*)-?.json', fname)
        print(match.group())
        exit(0)
        contest_timestamp_id = datetime.strptime(match, 'stats_%Y-%m-%d-%H-%M.json').strftime('%Y-%m-%d-%H-%M')
        
        # PROCESS REPLAYS: extract files
        replays_archive_name = 'replays_%s.tar.gz' % contest_timestamp_id
        replays_folder_name = 'replays_%s' % contest_timestamp_id
        replays_archive_full_path = os.path.join(DATA_URL, 'replays-archive', replays_archive_name)
        replays_folder_full_path = os.path.join(DATA_URL, 'replays-archive', replays_folder_name)

        print(f'\t Extract: {replays_archive_full_path}')
        os.system(f'mkdir {replays_folder_full_path}')
        os.system(f'tar zxf {replays_archive_full_path} -C {replays_folder_full_path}')

        # Create archive for each team
        for t in teams:
            replays_archive_name = f'replays_{t}.tar.gz'
            replays_archive_full_path = os.path.join(DATA_URL, 'replays-archive', replays_folder_name, replays_archive_name)
            os.system(f'tar zcf {replays_archive_full_path} {replays_folder_full_path}/*{t}*')
            print(f'\t Create tar for team {t}: {replays_archive_full_path}')



        # PROCESS LOGS: compress and upload
        logs_archive_name = 'logs_%s.tar.gz' % contest_timestamp_id
        logs_folder_name = 'logs_%s' % contest_timestamp_id
        logs_archive_full_path = os.path.join(DATA_URL, 'logs-archive', logs_archive_name)
        logs_folder_full_path = os.path.join(DATA_URL, 'logs-archive', logs_folder_name)

        print(f'\t Extract: {logs_archive_full_path}')

        os.system(f'mkdir {logs_folder_full_path}')
        os.system(f'tar zxf {logs_archive_full_path} -C {logs_folder_full_path}')


        # Create archive for each team
        for t in teams:
            logs_archive_name = f'logs_{t}.tar.gz'
            logs_archive_full_path = os.path.join(DATA_URL, 'logs-archive', logs_folder_name, logs_archive_name)
            os.system(f'tar zcf {logs_archive_full_path} {logs_folder_full_path}/*{t}*')
            print(f'\t Create tar for team {t}: {logs_archive_full_path}')

    
if __name__ == "__main__":
    main()