import requests
import xml.etree.ElementTree as ET
from typing import Dict, Tuple
import sqlite3
from pathlib import Path
import sys
from shutil import rmtree
from itertools import dropwhile
import json

# A semester is a combination of term + year

TERMS = ['spring', 'summer', 'fall', 'winter']
API_URL = "https://courses.illinois.edu/cisapp/explorer/schedule/"
DIRECTORIES = ['./runtime', './outputs']

epoch_term = ('fall', 2004)

LIMIT_SEMS = 0

# encode and decode semester because i'm lazy and don't want to deal with aggregate keys

def encode_semester(term, year):
    return (int(year) - epoch_term[1]) * 4 + TERMS.index(term) - 2

def decode_semester(code): # returns tuple: (term, year)
    code = code + 2
    return (TERMS[code % 4], str(2004 + (code // 4)))

def get_starting_semester():
    import datetime
    year = datetime.datetime.utcnow().year
    term = TERMS[-1] # winter start, work backwards
    return decode_semester(encode_semester(term, year) + 1) # but actually + 1 in case we want a spring semester from next year

EXAMPLE_XML = """
<ns2:term xmlns:ns2="http://rest.cis.illinois.edu" id="120230"><parents><calendarYear id="2023" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023.xml">2023</calendarYear></parents><label>Winter 2023</label><subjects><subject id="ACE" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ACE.xml">Agricultural and Consumer Economics</subject><subject id="ADV" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ADV.xml">Advertising</subject><subject id="AFAS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/AFAS.xml">Air Force Aerospace Studies</subject><subject id="ANSC" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ANSC.xml">Animal Sciences</subject><subject id="ART" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ART.xml">Art</subject><subject id="ASTR" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ASTR.xml">Astronomy</subject><subject id="ATMS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ATMS.xml">Atmospheric Sciences</subject><subject id="BADM" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/BADM.xml">Business Administration</subject><subject id="CHLH" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/CHLH.xml">Community Health</subject><subject id="CLCV" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/CLCV.xml">Classical Civilization</subject><subject id="CMN" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/CMN.xml">Communication</subject><subject id="DANC" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/DANC.xml">Dance</subject><subject id="ECON" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ECON.xml">Economics</subject><subject id="ENGL" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ENGL.xml">English</subject><subject id="ESE" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/ESE.xml">Earth, Society, and Environment</subject><subject id="GEOL" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/GEOL.xml">Geology</subject><subject id="GGIS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/GGIS.xml">Geography &amp; Geographic Information Science</subject><subject id="GLBL" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/GLBL.xml">Global Studies</subject><subject id="GWS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/GWS.xml">Gender and Women's Studies</subject><subject id="IS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/IS.xml">Information Sciences</subject><subject id="MACS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/MACS.xml">Media and Cinema Studies</subject><subject id="MUS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/MUS.xml">Music</subject><subject id="NS" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/NS.xml">Naval Science</subject><subject id="PHIL" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/PHIL.xml">Philosophy</subject><subject id="PSYC" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/PSYC.xml">Psychology</subject><subject id="REHB" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/REHB.xml">Rehabilitation Counseling</subject><subject id="REL" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/REL.xml">Religion</subject><subject id="RST" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/RST.xml">Recreation, Sport, and Tourism</subject><subject id="SOC" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/SOC.xml">Sociology</subject><subject id="SPAN" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/SPAN.xml">Spanish</subject><subject id="THEA" href="https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter/THEA.xml">Theatre</subject></subjects></ns2:term>
"""

# functions to handle fetching and parsing of XML on site
API_SCHEDULE = "https://courses.illinois.edu/cisapp/explorer/schedule"

def get_sem_xml(term, year):
    req = requests.get("/".join((API_SCHEDULE, year, f"{term}.xml")))
    print(req.url)
    return req.content

"""
Yields subjects (ACE, ADV, etc.) from a string representing an XML response (request specified semester)
ex. https://courses.illinois.edu/cisapp/explorer/schedule/2023/winter.xml

Outputs: 100 -> 161 -> 199 -> ...
"""
def iter_subjs_from_semester(text):
    tree = ET.fromstring(text)
    for subj in tree.iter('subject'):
        yield subj.get('id')

def get_sem_subj_xml(term, year, subj):
    req = requests.get("/".join((API_SCHEDULE, year, term, f"{subj}.xml")))
    print(req.url)
    return req.content
"""
Yields course numbers (101, 304, etc.) from a string representing an XML response (request specified semester + subject)
ex. https://courses.illinois.edu/cisapp/explorer/schedule/2023/fall/ACE.xml

Outputs: 100 -> 161 -> 199 -> ...
"""
def iter_course_num_from_semester_subject(text):
    tree = ET.fromstring(text)
    for course in tree.iter('course'):
        yield course.get('id')

# functions to handle committing to db
def data_layer_init():
    Path('./outputs').mkdir(exist_ok=True)
    con = sqlite3.connect('./outputs/offerings.db')
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS offerings(enc_term integer, subj text, course text)")
    return con, cur

def data_layer_dump(cur, term, year, subj, course):
    cur.execute("INSERT INTO offerings VALUES(?, ?, ?)", (encode_semester(term, year), subj, course))

def data_layer_commit(con):
    con.commit()

def data_layer_yield(cur):
    for row in cur.execute("select subj, course, group_concat(enc_term) from offerings group by subj, course"):
        yield (f"{row[0]}", f"{row[1]}", map(int, row[2].split(',')))

def data_layer_dump_to_json(cur, output_path):
    output = []
    for subj, num, sems in data_layer_yield(cur):
        output.append(
            {"fullName": f"{subj} {num}",
             "subject": subj,
             "number": num,
             "semesters": list(sems)
             }
        )
    with open(output_path, 'w') as of:
        return json.dump(output, fp=of)

# functions to handle process crashing

def remove_bookmark():
    Path('./runtime/bookmark.txt').unlink()

def set_bookmark(enc_sem, subj):
    Path('./runtime').mkdir(exist_ok=True)
    with open('./runtime/bookmark.txt', 'w') as f:
        f.write(str(enc_sem) + "\n")
        f.write(subj)

def get_bookmark():
    try:
        with open('./runtime/bookmark.txt', 'r') as f:
            return True, int(f.readline()), f.readline()
    except FileNotFoundError:
        return False, None, None

def full_exec():
    con, cur = data_layer_init()
    
    bookmarked_state, enc_starting_term, starting_subj = get_bookmark()
    if not bookmarked_state:
        enc_starting_term = encode_semester(*get_starting_semester())
    else:
        print("bookmark found at semester:", decode_semester(enc_starting_term), starting_subj)

    if LIMIT_SEMS > 0:
        term_stop = enc_starting_term - LIMIT_SEMS
    else:
        term_stop = -1
    for enc_sem in range(enc_starting_term, term_stop, -1):
        term, year = decode_semester(enc_sem)
        xml_with_subj = get_sem_xml(*decode_semester(enc_sem))
        if not xml_with_subj:
            print("warn: no content for", term, year)
            continue
        subj_list = sorted(list(iter_subjs_from_semester(xml_with_subj)))
        if bookmarked_state: # handle the bookmark
            bookmarked_state = False
            subj_list = dropwhile(lambda x: x != starting_subj, subj_list) # drop all preceding subjects
        for subj in subj_list:
            set_bookmark(enc_sem, subj) # set the bookmark so we can continue if we crash via throttling
            xml_with_course = get_sem_subj_xml(*decode_semester(enc_sem), subj)
            for course in iter_course_num_from_semester_subject(xml_with_course):
                print(term, year, subj, course)
                data_layer_dump(cur, term, year, subj, course) # write to sqlite db
            data_layer_commit(con) # commit
    remove_bookmark() # we are done so remove the bookmark

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-f', '-get'):
        if sys.argv[1] == '-f':
            print("removing existing products")
            for directory in DIRECTORIES:
                rmtree(directory)
        full_exec()
    con, cur = data_layer_init()
    # just some debug data printing
    for i, x in enumerate(data_layer_yield(cur)):
        print(x)
        if i > 30:
            break
    data_layer_dump_to_json(cur, './outputs/offerings.json')
        
