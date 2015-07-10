import json
import dateutil.parser
import getopt
import re
import http.cookiejar, urllib.request
from unidecode import unidecode
import sqlite3
import sys

API_KEY=""

def getPage (page):
    data = urllib.request.urlopen("http://apixha.ixxi.net/APIX?keyapp=" + API_KEY + page)
    return data.read().decode('utf-8')

def getLineDirections(db_conn, line):
    db_cursor = db_conn.cursor()
    return db_cursor.execute('select directions.d_name from directions, line_direction, lines where directions.d_id = line_direction.ld_dir_id and line_direction.ld_line_id = lines.l_id and lines.l_code = ?', (line,)).fetchall()

def getLineStations(db_conn, line):
    db_cursor = db_conn.cursor()
    return db_cursor.execute('SELECT st_name FROM stations, station_lines, lines WHERE stations.st_id = station_lines.sl_station_id and station_lines.sl_line_id = lines.l_id and lines.l_code = ?', (line,)).fetchall()

def getStationIdForLine(db_conn, line, station):
    db_cursor = db_conn.cursor()
    return db_cursor.execute('SELECT st_id, st_name FROM stations, station_lines, lines WHERE stations.st_id = station_lines.sl_station_id and station_lines.sl_line_id = lines.l_id and lines.l_code = ? and stations.st_name like ?', (line, "%"+station+"%")).fetchone()

def getLineId(db_conn, line):
    db_cursor = db_conn.cursor()
    return db_cursor.execute('SELECT l_id, l_code FROM lines where lines.l_code = ?', (line,)).fetchone()

def getNextStop(db_conn, line, station):
    line_id, line_code = getLineId(db_conn, line)
    stops = []
    station_id, station_name = getStationIdForLine(db_conn, line, station)
    data = json.loads(getPage('&cmd=getNextStopsRealtime&stopArea=%i&line=%i&withText=True&apixFormat=json' % (station_id, line_id)))
    for stop in data['nextStopsOnLines'][0]['nextStops']:
        nexttime = dateutil.parser.parse(stop['nextStopTime'])
        stops.append((nexttime.strftime("%H:%M"),
            line_code,
            station_name,
            stop['directionName']))
    return stops

def fetchAllStaticInfo(db_cursor):
    data = getPage("&cmd=getStopPlaces&engine=ratp&orderBy=alpha&withDetails=true&apixFormat=json")
    js = json.loads(data)
    for stop in js['stopPlaces']:
        try:
            db_cursor.execute("INSERT INTO stations (st_id, st_name, st_long, st_lat) VALUES (?, ?, ?, ?)", (stop['id'], stop['name'], stop['longitude'], stop['latitude']))
        except sqlite3.IntegrityError:
            pass
        for line in stop['lines']:
            try:
                db_cursor.execute("INSERT INTO lines (l_id, l_code, l_name) VALUES (?, ?, ?)", (line['id'], line['code'], line['name']))
            except sqlite3.IntegrityError:
                pass
            try:
                db_cursor.execute("INSERT INTO station_lines (sl_station_id, sl_line_id) VALUES (?, ?)", (stop['id'], line['id']))
            except sqlite3.IntegrityError:
                pass
            for direction in line['directions']:
                try:
                    db_cursor.execute("INSERT INTO directions (d_id, d_name) VALUES (?, ?)" , (direction['id'], direction['name']))
                except sqlite3.IntegrityError:
                    pass
                try:
                    db_cursor.execute("INSERT INTO line_direction (ld_dir_id, ld_line_id) VALUES (?, ?)", (direction['id'], line['id']))
                except sqlite3.IntegrityError:
                    pass
            try:
                db_cursor.execute("INSERT INTO line_groups (lg_id, lg_name) VALUES (?, ?)", (line['groupOfLines']['id'], line['groupOfLines']['name']))
            except sqlite3.IntegrityError:
                pass
            try:
                db_cursor.execute("INSERT INTO line_group_line (lgl_line_id, lgl_group_id) VALUES (?, ?)", (line['id'], line['groupOfLines']['id']))
            except sqlite3.IntegrityError:
                pass

def initDB(db_cursor):
    db_cursor.execute('CREATE TABLE IF NOT EXISTS stations (st_id INTEGER UNIQUE, st_name TEXT, st_long TEXT, st_lat TEXT)')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS lines (l_id INTEGER UNIQUE, l_code TEXT, l_name TEXT)')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS station_lines (sl_station_id INTEGER, sl_line_id INTEGER, UNIQUE(sl_station_id, sl_line_id))')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS line_groups (lg_id INTEGER UNIQUE, lg_name TEXT)')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS line_group_line (lgl_line_id INTEGER, lgl_group_id INTEGER, UNIQUE(lgl_line_id, lgl_group_id))')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS directions (d_id INTEGER UNIQUE, d_name TEXT)')
    db_cursor.execute('CREATE TABLE IF NOT EXISTS line_direction (ld_dir_id INTEGER, ld_line_id INTEGER, UNIQUE(ld_dir_id, ld_line_id))')

def fillDB(db_fname):
    conn = sqlite3.connect(db_fname)
    c = conn.cursor()
    initDB(c)
    fetchAllStaticInfo(c)
    conn.commit()
    conn.close()

def printUsage(name):
  print("Usage:\t%s -t transport_type -i database.db [-u] -l line [-s station [-d direction]] " % name)
#  print("\t%s -a -t transport_type -c cause" % name)
  print("\t-h: Display this help")
  print("\t-i database: static information database")
  print("\t-u: update the specified databased with static information")
  print("\t-l line: line number or name. e.g.: 72, A, T3")
  print("\t-s station: optionnal: station for which to print the next stops")
  print("\t-d destination: optionnal: destination for which to print the next stops")
#  print("\t-c cause: cause of the disturbance (alerte, travaux, or manif)")
#  print("\t-a: get alerts and transportation status (work on the line, manifestations)")


def main():
    type_transp = ''
    line = ''
    station = ''
    alert = False
    cause = ''
    destination = None
    dbname = None
    dbupdate = False

    try:
        opt, args = getopt.getopt(sys.argv[1:], "ahl:s:d:c:i:u", ["help"])
    except getopt.GetoptError:
        printUsage(sys.argv[0])
        return 1
    for op, val in opt:
        if op in ("-h", "--help"):
            printUsage(sys.argv[0])
            return 0
        elif op == "-l":
            line = val
        elif op == "-s":
            station = val
        elif op == "-d":
            destination = val
        elif op == "-i":
            dbname = val
        elif op == "-u":
            dbupdate = True

    if not dbname:
        printUsage(sys.argv[0])
        return 1
    if dbupdate:
        fillDB(dbname)
    if line:
        conn = sqlite3.connect(dbname)
        if station:
            for wait, line, station, direction in getNextStop(conn, line, station):
                print("Arrêt de la ligne %s à %s à %s, direction %s." % (line, station, wait, direction))
        else:
            for st in getLineStations(conn, line):
                print("- %s" % st)
        conn.close()

if __name__ == "__main__":
      sys.exit(main())
