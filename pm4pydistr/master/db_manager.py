import os
import sqlite3


class DbManager:
    def __init__(self, conf):
        self.conf = conf

    def create_log_db(self):
        database_path = self.conf + ".db"
        if not os.path.exists(database_path):
            conn = sqlite3.connect(database_path)
            curs = conn.cursor()
            curs.execute("CREATE TABLE SLAVES (CONF TEXT, ID TEXT)")
            curs.execute("CREATE TABLE LOGS (LOG_NAME TEXT, ID TEXT)")
            conn.commit()
            conn.close()

    def get_slaves_from_db(self):
        database_path = self.conf + ".db"
        slaves = {}
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        qr = curs.execute("SELECT CONF, ID FROM SLAVES")

        for res in qr.fetchall():
            slaves[str(res[0])] = str(res[1])

        conn.close()

        return slaves

    def get_logs_from_db(self):
        database_path = self.conf + ".db"
        logs = {}
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        qr = curs.execute("SELECT LOG_NAME, ID FROM LOGS")

        for res in qr.fetchall():
            logs[str(res[0])] = str(res[1])

        conn.close()

        return logs
