import csv
from tabulate import tabulate

TEAM_NAMES_FILE = 'AI17_team_registrations.csv'
SRC_TEAM_NAME_COL = 'Name of the team '
SRC_STUDENT_1_NO = 'Student number of member 1'
SRC_STUDENT_2_NO = 'Student number of member 2'
SRC_STUDENT_3_NO = 'Student number of member 3 (if any)'
SRC_STUDENT_4_NO = 'Student number of member 4 (if any)'

OUT_TEAM_NAME_COL = 'TEAM_NAME'
OUT_STUDENT_ID_COL = 'STUDENT_ID'


students_team = {}
with open(TEAM_NAMES_FILE, 'r') as f:
    reader = csv.reader(f, delimiter=',', quotechar='"')

    team_name_col_idx = None
    stud_1_col_idx = None
    stud_2_col_idx = None
    stud_3_col_idx = None
    stud_4_col_idx = None
    for row in reader:
        if team_name_col_idx is None:
            team_name_col_idx = row.index(SRC_TEAM_NAME_COL)
            stud_1_col_idx = row.index(SRC_STUDENT_1_NO)
            stud_2_col_idx = row.index(SRC_STUDENT_2_NO)
            stud_3_col_idx = row.index(SRC_STUDENT_3_NO)
            stud_4_col_idx = row.index(SRC_STUDENT_4_NO)
            continue

        if not row[team_name_col_idx]:
            continue

        team_name = row[team_name_col_idx]

        if row[stud_1_col_idx]:
            stud_id = 's' + row[stud_1_col_idx]
            students_team[stud_id] = team_name
        if row[stud_2_col_idx]:
            stud_id = 's' + row[stud_2_col_idx]
            students_team[stud_id] = team_name
        if row[stud_3_col_idx]:
            stud_id = 's' + row[stud_3_col_idx]
            students_team[stud_id] = team_name
        if row[stud_4_col_idx]:
            stud_id = 's' + row[stud_4_col_idx]
            students_team[stud_id] = team_name


with open('AI17_team_names.csv', 'w') as f:
    csv_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow([OUT_STUDENT_ID_COL,OUT_TEAM_NAME_COL])
    for stud_id, team_name in students_team.items():
        csv_writer.writerow([stud_id, team_name])

