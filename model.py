import pymysql

# 数据库配置信息
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    # 'password': 'h0ld?Fish:Palm',
    'password': 'admin',
    'database': 'agsun',
    'charset': 'utf8'
}


class DatabaseHandler:
    def __init__(self, host, user, password, database, charset):
        self.conn = pymysql.connect(host=host,
                                    user=user,
                                    password=password,
                                    database=database,
                                    charset=charset,
                                    cursorclass=pymysql.cursors.DictCursor)
        self.cursor = self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()


class Files:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_file_record(self, file_name, md5, file_path):
        sql = "INSERT INTO files (file_name, md5, file_path) VALUES (%s, %s, %s)"
        try:
            self.db_handler.cursor.execute(sql, (file_name, md5, file_path))
            self.db_handler.commit()
            print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")

    def query_file_by_md5(self, md5):
        sql = "SELECT * FROM files WHERE md5 = %s"
        self.db_handler.cursor.execute(sql, (md5,))
        return self.db_handler.cursor.fetchone()


db_handler = DatabaseHandler(host=DB_CONFIG['host'],
                             user=DB_CONFIG['user'],
                             password=DB_CONFIG['password'],
                             database=DB_CONFIG['database'],
                             charset=DB_CONFIG['charset'])
db_files = Files(db_handler)


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def select(self):  # 注意这里的改动，使用了self
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM `user` WHERE `username` = %s AND `password` = %s"
                print(sql)
                cursor.execute(sql, (self.username, self.password))  # 使用实例属性
                result = cursor.fetchone()
                if result:
                    return True
                else:
                    return False
        finally:
            connection.close()


class CheckPartCount:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_part_count` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                print(sql)
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result))
                connection.commit()
        finally:
            connection.close()


class CheckDiffpdf:
    def __init__(self, username, dataline, work_num, pdf_path1, pdf_name1, pdf_path2, pdf_name2, result, is_error):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path1 = pdf_path1
        self.pdf_name1 = pdf_name1
        self.pdf_path2 = pdf_path2
        self.pdf_name2 = pdf_name2
        self.result = result
        self.is_error = is_error

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_diff_pdf` (`username`, `dataline`, `work_num`, `pdf_path1`, `pdf_name1`,`pdf_path2`, `pdf_name2`, `result`, `is_error`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                print(sql)
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num, self.pdf_path1,
                               self.pdf_name1, self.pdf_path2, self.pdf_name2, self.result, self.is_error))
                connection.commit()
        finally:
            connection.close()


class CheckLanguage:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result, is_error):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result
        self.is_error = is_error

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_language` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`, `is_error`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                print(sql)
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result, self.is_error))
                connection.commit()
        finally:
            connection.close()


class CheckScrew:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result, is_error):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result
        self.is_error = is_error

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_screw` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`, `is_error`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                print(sql)
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result, self.is_error))
                connection.commit()
        finally:
            connection.close()


class CheckCE:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, excel_path, excel_name, work_table, result):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.excel_path = excel_path
        self.excel_name = excel_name
        self.work_table = work_table
        self.result = result

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_ce` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`,`excel_path`,`excel_name`,`work_table`,`result`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                print(sql)
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num, self.pdf_path,
                               self.pdf_name, self.excel_path, self.excel_name, self.work_table, self.result))
                connection.commit()
        finally:
            connection.close()


class CheckPageNumber:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result, is_error):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result
        self.is_error = is_error

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_pagenumber` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`, `is_error`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result, self.is_error))
                connection.commit()
        finally:
            connection.close()


class CheckLine:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result, result_file):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result
        self.result_file = result_file

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_line` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`, `result_file`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result, self.result_file))
                connection.commit()
        finally:
            connection.close()


class CheckCEsize:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result, is_error):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result
        self.is_error = is_error

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_size` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`, `is_error`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result, self.is_error))
                connection.commit()
        finally:
            connection.close()


class CheckArea:
    def __init__(self, username, dataline, work_num, pdf_path1, pdf_name1, pdf_path2, pdf_name2, result):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path1 = pdf_path1
        self.pdf_name1 = pdf_name1
        self.pdf_path2 = pdf_path2
        self.pdf_name2 = pdf_name2
        self.result = result

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_area` (`username`, `dataline`, `work_num`, `pdf_path1`, `pdf_name1`, `pdf_path2`, `pdf_name2`, `result`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path1, self.pdf_name1, self.pdf_path2, self.pdf_name2, self.result))
                connection.commit()
        finally:
            connection.close()


class CheckIcon:
    def __init__(self, username, dataline, work_num, pdf_path, pdf_name, result):
        self.username = username
        self.dataline = dataline
        self.work_num = work_num
        self.pdf_path = pdf_path
        self.pdf_name = pdf_name
        self.result = result

    def save_to_db(self):
        connection = pymysql.connect(host=DB_CONFIG['host'],
                                     user=DB_CONFIG['user'],
                                     password=DB_CONFIG['password'],
                                     database=DB_CONFIG['database'],
                                     charset=DB_CONFIG['charset'])
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO `check_icon` (`username`, `dataline`, `work_num`, `pdf_path`, `pdf_name`, `result`) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (self.username['username'], self.dataline, self.work_num,
                               self.pdf_path, self.pdf_name, self.result))
                connection.commit()
        finally:
            connection.close()
