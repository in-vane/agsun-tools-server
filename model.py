import pymysql
from datetime import datetime
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

    def insert_file_record(self, username, filename, path, md5):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        check_sql = "SELECT COUNT(*) as count FROM files WHERE md5 = %s AND path = %s"
        insert_sql = "INSERT INTO files (username, datetime, filename, path, md5) VALUES (%s, %s, %s, %s, %s)"

        try:
            # 检查是否存在相同的 md5 和 path
            self.db_handler.cursor.execute(check_sql, (md5, path))
            result = self.db_handler.cursor.fetchone()
            if result and result['count'] > 0:
                print("Record with the same md5 and path already exists. No insertion needed.")
            else:
                # 如果不存在，则插入新的记录
                self.db_handler.cursor.execute(insert_sql, (username, current_time, filename, path, md5))
                self.db_handler.commit()
                print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def query_file_by_md5(self, md5):
        sql = "SELECT * FROM files WHERE md5 = %s"
        self.db_handler.cursor.execute(sql, (md5,))
        return self.db_handler.cursor.fetchone()
class Result:
    def __init__(self, db_handler):
        self.db_handler = db_handler


    def insert_record(self, user_id, type_id, file_path, path, text):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_today = datetime.now().strftime('%Y-%m-%d')

        path = str(path)

        # 检查是否存在相同记录
        check_sql = """
            SELECT * FROM result 
            WHERE DATE(datetime) = %s 
            AND user_id = %s 
            AND type_id = %s 
            AND file_path = %s
        """
        self.db_handler.cursor.execute(check_sql, (date_today, user_id, type_id, file_path))
        existing_records = self.db_handler.cursor.fetchall()

        # 如果存在相同记录，删除这些记录
        if existing_records:
            delete_sql = """
                DELETE FROM result 
                WHERE DATE(datetime) = %s 
                AND user_id = %s 
                AND type_id = %s 
                AND file_path = %s
            """
            self.db_handler.cursor.execute(delete_sql, (date_today, user_id, type_id, file_path))
            self.db_handler.commit()

        # 插入新的记录
        insert_sql = """
            INSERT INTO result (datetime, user_id, type_id, file_path, path, text) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db_handler.cursor.execute(insert_sql, (current_time, user_id, type_id, file_path, path, text))
            self.db_handler.commit()
            print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def query_record(self, datetime, username, type_id, file_path):
        sql = "SELECT path, text FROM result WHERE DATE(datetime) = %s AND user_id = %s AND type_id = %s AND file_path = %s"
        self.db_handler.cursor.execute(sql, (datetime, username, type_id, file_path))
        rows = self.db_handler.cursor.fetchall()

        paths = [row['path'] for row in rows]
        texts = [row['text'] for row in rows]
        texts = texts[0]
        return paths, texts
class Area:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, file1_path, file2_path, image1_path, image2_path, image_result):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 定义插入SQL语句
        sql = """
            INSERT INTO area (datetime, user_id, type_id, file1_path, file2_path, image1_path, image2_path, result_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
        try:
            self.db_handler.cursor.execute(sql, (
                current_time, user_id, type_id, file1_path, file2_path, image1_path, image2_path, image_result))
            self.db_handler.commit()
            print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
class Ocr:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, md5, image1_path, image2_path, image_result):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 定义插入SQL语句
        image_result = str(image_result)
        sql = """
            INSERT INTO ocr (datetime, user_id, type_id, file_md5, image1_path, image2_path, result_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
        try:
            self.db_handler.cursor.execute(sql, (
                current_time, user_id, type_id, md5, image1_path, image2_path, image_result))
            self.db_handler.commit()
            print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
class Line_Result_Files:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_file_record(self, user_id, type_id, file_path, output_path):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_today = datetime.now().strftime('%Y-%m-%d')

        # 检查是否存在相同记录
        check_sql = """
               SELECT id FROM line_result_files 
               WHERE DATE(datetime) = %s 
               AND user_id = %s 
               AND file_path = %s
           """

        # 删除已有记录的SQL
        delete_sql = """
               DELETE FROM line_result_files 
               WHERE id = %s
           """

        # 插入新的记录的SQL
        insert_sql = """
               INSERT INTO line_result_files (user_id, type_id, datetime, file_path, path) 
               VALUES (%s, %s, %s, %s, %s)
           """

        try:
            # 检查是否存在相同记录
            self.db_handler.cursor.execute(check_sql, (date_today, user_id, file_path))
            existing_records = self.db_handler.cursor.fetchall()

            # 如果存在相同记录，删除这些记录
            for record in existing_records:
                record_id = record['id']
                self.db_handler.cursor.execute(delete_sql, (record_id,))

            # 插入新的记录
            self.db_handler.cursor.execute(insert_sql, (user_id, type_id, current_time, file_path, output_path))
            self.db_handler.commit()
            print("File record inserted successfully.")

        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def query_record(self, datetime, user_id, type_id, file_md5):
        sql = "SELECT path FROM line_result_files WHERE DATE(datetime) = %s AND user_id = %s AND type_id = %s AND file_md5 = %s"
        self.db_handler.cursor.execute(sql, (datetime, user_id, type_id, file_md5))
        return [row['path'] for row in self.db_handler.cursor.fetchall()]
class Diff_Pdf:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, file1_path, file2_path, path, text):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today_date = datetime.now().strftime('%Y-%m-%d')

        # 将 path 转换为字符串
        path = str(path)

        # SQL 查询语句，用于检测是否存在相同记录
        check_sql = """
               SELECT id FROM diff_pdf 
               WHERE DATE(datetime) = %s 
               AND user_id = %s 
               AND type_id = %s 
               AND file1_path = %s 
               AND file2_path = %s
           """

        # SQL 删除语句，用于删除已有记录
        delete_sql = """
               DELETE FROM diff_pdf 
               WHERE id = %s
           """

        # SQL 插入语句
        insert_sql = """
               INSERT INTO diff_pdf (datetime, user_id, type_id, file1_path, file2_path, path, text)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
           """

        try:
            # 检查是否存在相同记录
            self.db_handler.cursor.execute(check_sql, (today_date, user_id, type_id, file1_path, file2_path))
            existing_records = self.db_handler.cursor.fetchall()

            # 如果存在相同记录，删除这些记录
            for record in existing_records:
                record_id = record['id']
                self.db_handler.cursor.execute(delete_sql, (record_id,))

            # 插入新的记录
            self.db_handler.cursor.execute(insert_sql, (
                current_time, user_id, type_id, file1_path, file2_path, path, text))
            self.db_handler.commit()
            print("File record inserted successfully.")

        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def query_record(self, datetime, username, type_id, file1_path, file2_path):
        sql = """
                   SELECT path, text
                   FROM diff_pdf
                   WHERE DATE(datetime) = %s AND user_id = %s AND type_id = %s AND file1_md5 = %s AND file2_md5 = %s
                   """
        self.db_handler.cursor.execute(sql, (datetime, username, type_id, file1_path, file2_path))
        rows = self.db_handler.cursor.fetchall()

        paths = [row['path'] for row in rows]
        texts = [row['text'] for row in rows]
        return paths, texts
class Ce:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, file1_md5, file2_md5, path):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        path = str(path)
        # 定义插入SQL语句
        sql = """
            INSERT INTO ce (datetime, user_id, type_id, file1_md5, file2_md5, path)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        try:
            self.db_handler.cursor.execute(sql, (
                current_time, user_id, type_id, file1_md5, file2_md5, path))
            self.db_handler.commit()
            print("File record inserted successfully.")
        except pymysql.IntegrityError as e:
            print(f"Error occurred while inserting file record: {e}")

    def query_record(self, datetime, username, type_id, file1_md5, file2_md5):
        sql = "SELECT path FROM ce WHERE DATE(datetime) = %s AND user_id = %s AND type_id = %s AND file1_md5 = %s AND file2_md5 = %s LIMIT 1"
        self.db_handler.cursor.execute(sql, (datetime, username, type_id, file1_md5, file2_md5))
        result = self.db_handler.cursor.fetchone()
        if result:
            path = result['path']
            return path
        return None
db_handler = DatabaseHandler(host=DB_CONFIG['host'],
                             user=DB_CONFIG['user'],
                             password=DB_CONFIG['password'],
                             database=DB_CONFIG['database'],
                             charset=DB_CONFIG['charset'])
db_files = Files(db_handler)
# 创建Files类的实例
db_ce = Ce(db_handler)

# 创建result类的实例
db_result = Result(db_handler)

# 创建Files类的实例
db_diff_pdf = Diff_Pdf(db_handler)
# 创建Files类的实例
db_line_result_files = Line_Result_Files(db_handler)
# 创建images类的实例
db_ocr = Ocr(db_handler)
# 创建images类的实例
db_area = Area(db_handler)


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
