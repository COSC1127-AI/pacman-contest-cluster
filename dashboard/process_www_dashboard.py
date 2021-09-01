
import tarfile
import shutil
import os
import json  
import re
from datetime import datetime
import re

DATA_URL = '/mnt/ssardina-pacman/cosc1125-1127-AI/www/feedback-final/'

def main():
    json_files = sorted([f for f in os.listdir(f'{DATA_URL}/stats-archive/') if os.path.isfile(os.path.join(DATA_URL,'stats-archive', f))], reverse=True)

    print(f'{DATA_URL}/stats-archive/')
    print(json_files)
    for fname in json_files:
        with open(f'{DATA_URL}/stats-archive/{fname}') as f: 
            d = json.load(f) 

        teams = d['team_stats'].keys()
        print(fname)
        match = re.match('stats_(.*).json', fname)
        contest_timestamp_id = match.group(1)
        
        # PROCESS REPLAYS: extract files
        replays_archive_name = 'replays_%s.tar.gz' % contest_timestamp_id
        replays_folder_name = 'replays_%s' % contest_timestamp_id
        replays_archive_full_path = os.path.join(DATA_URL, 'replays-archive', replays_archive_name)
        replays_folder_full_path = os.path.join(DATA_URL, 'replays-archive', replays_folder_name)

        print(f'======> Extract: {replays_archive_full_path}')

        # If this as already extracted, skip it...
        if os.path.exists(replays_folder_full_path):
            print('\t .. exist already, skipping')
            continue

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

        print(f'======> Extract: {logs_archive_full_path}')

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
