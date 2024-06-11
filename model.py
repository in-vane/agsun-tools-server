import pymysql
from datetime import datetime
import ast
from utils import process_paths, merge_records, add_url

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

    def insert_file_record(self, username, file_name, md5, file_path):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        check_sql = "SELECT COUNT(*) as count FROM files WHERE md5 = %s AND file_path = %s"
        insert_sql = "INSERT INTO files (username, datetime, file_name, md5, file_path) VALUES (%s, %s, %s, %s, %s)"
        update_sql = "UPDATE files SET username = %s, datetime = %s WHERE md5 = %s AND file_path = %s"

        try:
            # 检查是否存在相同的 md5 和 file_path
            self.db_handler.cursor.execute(check_sql, (md5, file_path))
            result = self.db_handler.cursor.fetchone()
            if result and result['count'] > 0:
                print("Record with the same md5 and file_path already exists. Updating username and datetime.")
                # 更新现有记录的 username 和 datetime
                self.db_handler.cursor.execute(update_sql, (username, current_time, md5, file_path))
                self.db_handler.commit()
                print("File record updated successfully.")
            else:
                # 如果不存在，则插入新的记录
                self.db_handler.cursor.execute(insert_sql, (username, current_time, file_name, md5, file_path))
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

    def query_files(self, table, datetime_str, username=None, type_id=None):
        print(f"Querying table: {table} for date: {datetime_str}, user: {username}, type_id: {type_id}")

        if type_id and type_id in ['003', '004', '005', '007', '008', '009', '010']:
            # 连表查询，获取 file_path, file_name 和 file_datetime
            sql = f"""
                SELECT t.file_path, f.file_name, f.datetime AS file_datetime
                FROM {table} t
                JOIN files f ON t.file_path = f.file_path
                WHERE DATE(t.datetime) = %s
            """
            params = [datetime_str]
            if username:
                sql += " AND t.user_id = %s"
                params.append(username)
            if type_id:
                sql += " AND t.type_id = %s"
                params.append(type_id)
        else:
            # 连表查询，获取 file1_path, file2_path, 和对应的 file_name, file_datetime
            sql = f"""
                SELECT t.file1_path, f1.file_name AS file1_name, f1.datetime AS file1_datetime,
                       t.file2_path, f2.file_name AS file2_name, f2.datetime AS file2_datetime
                FROM {table} t
                LEFT JOIN files f1 ON t.file1_path = f1.file_path
                LEFT JOIN files f2 ON t.file2_path = f2.file_path
                WHERE DATE(t.datetime) = %s
            """
            params = [datetime_str]
            if username:
                sql += " AND t.user_id = %s"
                params.append(username)
            if type_id:
                sql += " AND t.type_id = %s"
                params.append(type_id)

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        results = self.db_handler.cursor.fetchall()
        print(results)

        # 构建结果
        result = []
        if type_id and type_id in ['003', '004', '005', '007', '008', '009', '010']:
            for row in results:
                result.append({
                    "file_name": row['file_name'],
                    "file_path": row['file_path'],
                    "file_datetime": row['file_datetime'].strftime('%Y-%m-%d %H:%M:%S')
                })
        else:
            for row in results:
                if row['file1_path'] and row['file1_name'] and row['file1_datetime']:
                    result.append({
                        "file_name": row['file1_name'],
                        "file_path": row['file1_path'],
                        "file_datetime": row['file1_datetime'].strftime('%Y-%m-%d %H:%M:%S')
                    })
                if row['file2_path'] and row['file2_name'] and row['file2_datetime']:
                    result.append({
                        "file_name": row['file2_name'],
                        "file_path": row['file2_path'],
                        "file_datetime": row['file2_datetime'].strftime('%Y-%m-%d %H:%M:%S')
                    })
        return result

class Result:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, file_path, path, text):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_today = datetime.now().strftime('%Y-%m-%d')
        path = str(path)
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

    def query_record(self, datetime=None, username=None, type_id=None, file_paths=None):
        # 基本的 SQL 查询语句
        sql = """
            SELECT r.user_id, r.datetime, r.type_id, r.file_path, r.text, r.path AS images, f.file_name
            FROM result r
            JOIN files f ON r.file_path = f.file_path
            WHERE 1=1
        """
        params = []

        # 根据传入参数动态添加查询条件
        if datetime:
            sql += " AND DATE(r.datetime) = %s"
            params.append(datetime)
        if username:
            sql += " AND r.user_id = %s"
            params.append(username)
        if type_id:
            sql += " AND r.type_id = %s"
            params.append(type_id)
        if file_paths:
            sql += " AND ("
            for i, file_path in enumerate(file_paths):
                if i > 0:
                    sql += " OR "
                sql += "r.file_path = %s"
                params.append(file_path)
            sql += ")"

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        rows = self.db_handler.cursor.fetchall()

        result = []
        for row in rows:
            # 将 datetime 转换为指定的字符串格式
            formatted_datetime = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": row['text'],
                "images": row['images'],
                "related_files": [
                    {
                        "file_name": row['file_name'],
                        "file_path": row['file_path']
                    }
                ],
                "result_file": ""
            }
            # 处理空字符串的情况
            if not record['images'].strip():
                record['images'] = []
            else:
                try:
                    # 使用 ast.literal_eval 将字符串转换为列表
                    record['images'] = ast.literal_eval(record['images'])
                    # 确保转换后的结果是一个列表
                    if not isinstance(record['images'], list):
                        raise ValueError("The input string does not represent a list")
                except (ValueError, SyntaxError):
                    raise ValueError("Invalid input string")
            record['images'] = process_paths(record['images'])
            result.append(record)

        print(result)
        print(len(result))
        return result
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

    def query_record(self, datetime=None, username=None, type_id=None, file_paths=None):
        # 基本的 SQL 查询语句
        sql = """
            SELECT a.user_id, a.datetime, a.type_id, a.file1_path, a.file2_path, a.result_path AS images,
                   f1.file_name AS file1_name, f1.file_path AS file1_path,
                   f2.file_name AS file2_name, f2.file_path AS file2_path
            FROM area a
            LEFT JOIN files f1 ON a.file1_path = f1.file_path
            LEFT JOIN files f2 ON a.file2_path = f2.file_path
            WHERE 1=1
        """
        params = []

        # 根据传入参数动态添加查询条件
        if datetime:
            sql += " AND DATE(a.datetime) = %s"
            params.append(datetime)
        if username:
            sql += " AND a.user_id = %s"
            params.append(username)
        if type_id:
            sql += " AND a.type_id = %s"
            params.append(type_id)
        if file_paths:
            if len(file_paths) == 1:
                sql += " AND (a.file1_path = %s OR a.file2_path = %s)"
                params.append(file_paths[0])
                params.append(file_paths[0])
            elif len(file_paths) == 2:
                sql += " AND ((a.file1_path = %s AND a.file2_path = %s) OR (a.file1_path = %s AND a.file2_path = %s))"
                params.append(file_paths[0])
                params.append(file_paths[1])
                params.append(file_paths[1])
                params.append(file_paths[0])

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        rows = self.db_handler.cursor.fetchall()

        result = []
        for row in rows:
            # 将 datetime 转换为指定的字符串格式
            formatted_datetime = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": "",  # text 直接设置为空字符串
                "images": row['images'],
                "related_files": [
                    {
                        "file_name": row['file1_name'],
                        "file_path": row['file1_path']
                    },
                    {
                        "file_name": row['file2_name'],
                        "file_path": row['file2_path']
                    }
                ],
                "result_file": row['images']
            }
            # 处理空字符串的情况
            if not record['images'].strip():
                record['images'] = []
            else:
                try:
                    # 如果不是列表，将其包装成列表
                    if not (record['images'].startswith('[') and record['images'].endswith(']')):
                        record['images'] = [record['images']]
                    else:
                        # 使用 ast.literal_eval 将字符串转换为列表
                        record['images'] = ast.literal_eval(record['images'])
                    # 确保转换后的结果是一个列表
                    if not isinstance(record['images'], list):
                        raise ValueError("The input string does not represent a list")
                except (ValueError, SyntaxError):
                    raise ValueError("Invalid input string")
            record['images'] = process_paths(record['images'])
            result.append(record)
        result = merge_records(result)
        print(result)
        print(len(result))
        return result


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
               INSERT INTO line_result_files (user_id, type_id, datetime, file_path, result_file) 
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

    def query_record(self, datetime=None, user_id=None, type_id=None, file_paths=None):
        print(f"条件是{datetime, user_id, type_id, file_paths}")
        # 基本的 SQL 查询语句
        sql = """
            SELECT lrf.user_id, lrf.datetime, lrf.type_id, lrf.result_file AS result_file,
                   f.file_name AS file_name, f.file_path AS file_path
            FROM line_result_files lrf
            LEFT JOIN files f ON lrf.file_path = f.file_path
            WHERE 1=1
        """
        params = []

        # 根据传入参数动态添加查询条件
        if datetime:
            sql += " AND DATE(lrf.datetime) = %s"
            params.append(datetime)
        if user_id:
            sql += " AND lrf.user_id = %s"
            params.append(user_id)
        if type_id:
            sql += " AND lrf.type_id = %s"
            params.append(type_id)
        if file_paths:
            sql += " AND ("
            for i, file_path in enumerate(file_paths):
                if i > 0:
                    sql += " OR "
                sql += "lrf.file_path = %s"
                params.append(file_path)
            sql += ")"

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        rows = self.db_handler.cursor.fetchall()

        result = []
        for row in rows:
            # 将 datetime 转换为指定的字符串格式
            formatted_datetime = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": "",
                "images": [],
                "related_files": [
                    {
                        "file_name": row['file_name'],
                        "file_path": row['file_path']
                    }
                ],
                "result_file": add_url(row['result_file'])  # 更新为从数据库获取的result_file
            }

            result.append(record)
        print(result)
        return result


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

    def query_record(self, datetime=None, username=None, type_id=None, file_paths=None):
        # 基本的 SQL 查询语句
        sql = """
               SELECT diff_pdf.user_id, diff_pdf.datetime, diff_pdf.type_id, diff_pdf.path AS images, diff_pdf.text,
                      f1.file_name AS file1_name, f1.file_path AS file1_path,
                      f2.file_name AS file2_name, f2.file_path AS file2_path
               FROM diff_pdf
               LEFT JOIN files f1 ON diff_pdf.file1_path = f1.file_path
               LEFT JOIN files f2 ON diff_pdf.file2_path = f2.file_path
               WHERE 1=1
           """
        params = []

        # 根据传入参数动态添加查询条件
        if datetime:
            sql += " AND DATE(diff_pdf.datetime) = %s"
            params.append(datetime)
        if username:
            sql += " AND diff_pdf.user_id = %s"
            params.append(username)
        if type_id:
            sql += " AND diff_pdf.type_id = %s"
            params.append(type_id)
        if file_paths:
            if len(file_paths) == 1:
                sql += " AND (diff_pdf.file1_path = %s OR diff_pdf.file2_path = %s)"
                params.append(file_paths[0])
                params.append(file_paths[0])
            elif len(file_paths) == 2:
                sql += " AND ((diff_pdf.file1_path = %s AND diff_pdf.file2_path = %s) OR (diff_pdf.file1_path = %s AND diff_pdf.file2_path = %s))"
                params.append(file_paths[0])
                params.append(file_paths[1])
                params.append(file_paths[1])
                params.append(file_paths[0])

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        rows = self.db_handler.cursor.fetchall()

        result = []
        for row in rows:
            # 将 datetime 转换为指定的字符串格式
            formatted_datetime = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')

            # 确定 file_name 和 file_path
            if file_paths:
                if len(file_paths) == 1:
                    if row['file1_path'] == file_paths[0]:
                        file_name = row['file1_name']
                        file_path_value = row['file1_path']
                    else:
                        file_name = row['file2_name']
                        file_path_value = row['file2_path']
                elif len(file_paths) == 2:
                    if row['file1_path'] == file_paths[0] and row['file2_path'] == file_paths[1]:
                        file_name = row['file1_name']
                        file_path_value = row['file1_path']
                    else:
                        file_name = row['file2_name']
                        file_path_value = row['file2_path']
            else:
                if row['file1_path']:
                    file_name = row['file1_name']
                    file_path_value = row['file1_path']
                else:
                    file_name = row['file2_name']
                    file_path_value = row['file2_path']

            # 将 images 字段从字符串转换为列表
            try:
                images_list = ast.literal_eval(row['images'])
            except (ValueError, SyntaxError):
                images_list = row['images']  # 如果转换失败，则保持原始字符串

            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": row['text'],
                "images": row['images'],
                "related_files": [
                    {
                        "file_name": row['file1_name'],
                        "file_path": row['file1_path']
                    },
                    {
                        "file_name": row['file2_name'],
                        "file_path": row['file2_path']
                    }
                ],
                "result_file": ""
            }
            result.append(record)
        print(result)
        print(len(result))
        return result


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

    def query_record(self, datetime=None, username=None, type_id=None, file_paths=None):
        # 基本的 SQL 查询语句
        sql = """
            SELECT ce.user_id, ce.datetime, ce.type_id, ce.path AS images,
                   f1.file_name AS file1_name, f1.file_path AS file1_path,
                   f2.file_name AS file2_name, f2.file_path AS file2_path
            FROM ce
            LEFT JOIN files f1 ON ce.file1_path = f1.file_path
            LEFT JOIN files f2 ON ce.file2_path = f2.file_path
            WHERE 1=1
        """
        params = []

        # 根据传入参数动态添加查询条件
        if datetime:
            sql += " AND DATE(ce.datetime) = %s"
            params.append(datetime)
        if username:
            sql += " AND ce.user_id = %s"
            params.append(username)
        if type_id:
            sql += " AND ce.type_id = %s"
            params.append(type_id)
        if file_paths:
            if len(file_paths) == 1:
                sql += " AND (ce.file1_path = %s OR ce.file2_path = %s)"
                params.append(file_paths[0])
                params.append(file_paths[0])
            elif len(file_paths) == 2:
                sql += " AND ((ce.file1_path = %s AND ce.file2_path = %s) OR (ce.file1_path = %s AND ce.file2_path = %s))"
                params.append(file_paths[0])
                params.append(file_paths[1])
                params.append(file_paths[1])
                params.append(file_paths[0])

        # 执行查询
        self.db_handler.cursor.execute(sql, params)
        rows = self.db_handler.cursor.fetchall()

        result = []
        for row in rows:
            # 将 datetime 转换为指定的字符串格式
            formatted_datetime = row['datetime'].strftime('%Y-%m-%d %H:%M:%S')

            # 确定 file_name 和 file_path
            file1_name = row['file1_name']
            file1_path = row['file1_path']
            file2_name = row['file2_name']
            file2_path = row['file2_path']

            # 将 images 字段从字符串转换为列表
            try:
                images_list = ast.literal_eval(row['images'])
            except (ValueError, SyntaxError):
                images_list = row['images']  # 如果转换失败，则保持原始字符串

            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": "",  # text 直接设置为空字符串
                "images": process_paths(images_list),
                "related_files": [
                    {
                        "file_name": file1_name,
                        "file_path": file1_path
                    },
                    {
                        "file_name": file2_name,
                        "file_path": file2_path
                    }
                ],
                "result_file": ""
            }
            result.append(record)
        print(result)
        return result


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

# result = db_files.query_files("diff_pdf",'2024-06-05','admin','002')

# db_files.query_files("result",'2024-06-05','admin','004')
# db_result.query_record('2024-06-08','admin','004')
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
