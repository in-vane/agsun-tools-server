import pymysql
from datetime import datetime
import ast
from utils import process_paths, merge_records, add_url
from DBUtils.PooledDB import PooledDB

# 数据库配置信息
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'h0ld?Fish:Palm',
    # 'password': 'admin',
    'database': 'agsun',
    'charset': 'utf8'
}

# 配置数据库连接池
POOL = PooledDB(
    creator=pymysql,
    maxconnections=50,  # 连接池最大连接数，适当设置为比用户数多一些
    mincached=5,        # 初始化时连接池中至少创建的空闲连接数
    maxcached=10,       # 连接池中最多可用的空闲连接数
    blocking=True,      # 达到最大连接数时是否阻塞
    maxusage=None,      # 每个连接最多重复使用的次数，None 表示无限制
    setsession=[],      # 开始会话前执行的命令列表
    ping=1,             # 检查连接的状态
    host=DB_CONFIG['host'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    db=DB_CONFIG['database'],
    charset=DB_CONFIG['charset'],
    cursorclass=pymysql.cursors.DictCursor  # 重点在这里
)

class DatabaseHandler:
    def __init__(self):
        self.conn = POOL.connection()
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

    def query_files(self, table, datetime_range, username=None, type_id=None):
        start_date, end_date = datetime_range
        print(
            f"Querying table: {table} for date range: {start_date} to {end_date}, user: {username}, type_id: {type_id}")

        params = [start_date, end_date]
        additional_conditions = ""

        if username:
            additional_conditions += " AND t.user_id = %s"
            params.append(username)
        if type_id:
            additional_conditions += " AND t.type_id = %s"
            params.append(type_id)

        if type_id and type_id in ['003', '004', '005', '007', '008', '009', '010']:
            # 连表查询，获取 file_path, file_name 和 file_datetime
            sql = f"""
                SELECT t.file_path, f.file_name, f.datetime AS file_datetime
                FROM {table} t
                JOIN files f ON t.file_path = f.file_path
                WHERE DATE(t.datetime) BETWEEN %s AND %s {additional_conditions}
            """
        else:
            # 连表查询，获取 file1_path, file2_path, 和对应的 file_name, file_datetime
            sql = f"""
                SELECT t.file1_path, f1.file_name AS file1_name, f1.datetime AS file1_datetime,
                       t.file2_path, f2.file_name AS file2_name, f2.datetime AS file2_datetime
                FROM {table} t
                LEFT JOIN files f1 ON t.file1_path = f1.file_path
                LEFT JOIN files f2 ON t.file2_path = f2.file_path
                WHERE DATE(t.datetime) BETWEEN %s AND %s {additional_conditions}
            """

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
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            start_date, end_date = datetime
            sql += " AND DATE(r.datetime) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
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
                        "file_path": add_url(row['file_path'])
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
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            start_date, end_date = datetime
            sql += " AND DATE(a.datetime) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        if username:
            sql += " AND a.user_id = %s"
            params.append(username)
        if type_id:
            sql += " AND a.type_id = %s"
            params.append(type_id)
        if file_paths:
            if len(file_paths) == 1:
                sql += " AND (a.file1_path = %s OR a.file2_path = %s)"
                params.extend([file_paths[0], file_paths[0]])
            elif len(file_paths) == 2:
                sql += " AND ((a.file1_path = %s AND a.file2_path = %s) OR (a.file1_path = %s AND a.file2_path = %s))"
                params.extend([file_paths[0], file_paths[1], file_paths[1], file_paths[0]])

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
                        "file_path": add_url(row['file1_path'])
                    },
                    {
                        "file_name": row['file2_name'],
                        "file_path": add_url(row['file2_path'])
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
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            start_date, end_date = datetime
            sql += " AND DATE(lrf.datetime) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
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
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            start_date, end_date = datetime
            sql += " AND DATE(diff_pdf.datetime) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
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
            file1_name = row['file1_name']
            file1_path = row['file1_path']
            file2_name = row['file2_name']
            file2_path = row['file2_path']

            # 将 images 字段从字符串转换为列表
            try:
                images_list = ast.literal_eval(row['images'])
            except (ValueError, SyntaxError):
                images_list = row['images']  # 如果转换失败，则保持原始字符串

            related_files = []
            if file1_path:
                related_files.append({
                    "file_name": file1_name,
                    "file_path": add_url(file1_path) if file1_path else None
                })
            if file2_path:
                related_files.append({
                    "file_name": file2_name,
                    "file_path": add_url(file2_path) if file2_path else None
                })

            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": row['text'],
                "images": images_list,
                "related_files": related_files,
                "result_file": ""
            }
            record['images'] = process_paths(record['images'])
            result.append(record)
        return result
class Ce:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def insert_record(self, user_id, type_id, file1_path, file2_path, path):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        path = str(path)
        # 定义插入SQL语句
        sql = """
            INSERT INTO ce (datetime, user_id, type_id, file1_path, file2_path, path)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        try:
            self.db_handler.cursor.execute(sql, (
                current_time, user_id, type_id, file1_path, file2_path, path))
            self.db_handler.commit()
            # 添加的打印语句
            print(f"用户 {user_id}，使用功能 {type_id}，时间为 {current_time}。")
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
            start_date, end_date = datetime
            sql += " AND DATE(ce.datetime) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
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

            related_files = []
            if file1_path:
                related_files.append({
                    "file_name": file1_name,
                    "file_path": add_url(file1_path) if file1_path else None
                })
            if file2_path:
                related_files.append({
                    "file_name": file2_name,
                    "file_path": add_url(file2_path) if file2_path else None
                })

            record = {
                "username": row['user_id'],
                "datetime": formatted_datetime,
                "type_id": row['type_id'],
                "text": "",  # text 直接设置为空字符串
                "images": images_list,
                "related_files": related_files,
                "result_file": ""
            }
            record['images'] = process_paths(record['images'])
            result.append(record)
        print(result)
        return result
db_handler = DatabaseHandler()
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

from datetime import datetime, timedelta

class UserFeatureRecordCount:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        # 定义所有的功能类型及其对应的表和 type_id（如果适用）
        self.features = [
            {'feature': 'ce表对比', 'table': 'ce', 'type_id': None},
            {'feature': '区域对比', 'table': 'area', 'type_id': None},
            {'feature': '整页对比', 'table': 'diff_pdf', 'type_id': None},
            {'feature': '线段检测', 'table': 'line_result_files', 'type_id': None},
            {'feature': '零件计数', 'table': 'result', 'type_id': '003'},
            {'feature': '页码检查', 'table': 'result', 'type_id': '004'},
            {'feature': '螺丝包', 'table': 'result', 'type_id': '005'},
            {'feature': 'ce贴纸尺寸', 'table': 'result', 'type_id': '007'},
            {'feature': '语言顺序', 'table': 'result', 'type_id': '008'},
        ]

    def get_user_record(self, date=None):
        """
        查询包含 datetime 字段的用户功能记录，并根据日期范围过滤（可选）。

        :param date: 列表，包含两个日期字符串 ['YYYY-MM-DD', 'YYYY-MM-DD']，可选
        :return: dict，格式化后的结果字典
        """
        # 处理日期范围
        if date:
            start_date, end_date = date
        else:
            # 默认最近30天
            end_date_dt = datetime.now()
            start_date_dt = end_date_dt - timedelta(days=30)
            start_date = start_date_dt.strftime('%Y-%m-%d')
            end_date = end_date_dt.strftime('%Y-%m-%d')

        # 动态构建 SQL 查询
        union_queries = []
        params = []
        for feature in self.features:
            query = f"SELECT u.username, '{feature['feature']}' AS feature, COUNT(r.datetime) AS record_count, GROUP_CONCAT(DISTINCT DATE(r.datetime)) AS datetime\n"
            if feature['type_id']:
                # 将日期条件和 type_id 移到 JOIN 子句中
                query += f"FROM user u\nLEFT JOIN {feature['table']} r ON u.username = r.user_id AND r.type_id = %s AND DATE(r.datetime) BETWEEN %s AND %s\n"
                params.extend([feature['type_id'], start_date, end_date])
            else:
                # 仅将日期条件移到 JOIN 子句中
                query += f"FROM user u\nLEFT JOIN {feature['table']} r ON u.username = r.user_id AND DATE(r.datetime) BETWEEN %s AND %s\n"
                params.extend([start_date, end_date])

            query += "GROUP BY u.username"
            union_queries.append(query)

        final_sql = " UNION ALL ".join(union_queries) + ";"

        try:
            self.db_handler.cursor.execute(final_sql, params)
            results = self.db_handler.cursor.fetchall()

            # 格式化结果
            formatted_results = {}

            for row in results:
                username = row['username']
                feature = row['feature']
                record_count = row['record_count']
                datetime_list = row['datetime'].split(',') if row['datetime'] else []

                if username not in formatted_results:
                    # 初始化所有功能
                    formatted_results[username] = {
                        feature_entry['feature']: {'record_count': 0, 'datetime': []}
                        for feature_entry in self.features
                    }

                # 更新记录数和日期
                formatted_results[username][feature]['record_count'] = record_count
                formatted_results[username][feature]['datetime'] = datetime_list

            return formatted_results
        except Exception as e:
            print(f"An error occurred while querying user feature record count: {e}")
            return {}

    def get_user_record_datetime(self, date=None):
        """
        查询不包含 datetime 字段的用户功能记录，并根据日期范围过滤（可选）。

        :param date: 列表，包含两个日期字符串 ['YYYY-MM-DD', 'YYYY-MM-DD']，可选
        :return: dict，格式化后的结果字典
        """
        # 处理日期范围
        if date:
            start_date, end_date = date
        else:
            # 默认最近30天
            end_date_dt = datetime.now()
            start_date_dt = end_date_dt - timedelta(days=30)
            start_date = start_date_dt.strftime('%Y-%m-%d')
            end_date = end_date_dt.strftime('%Y-%m-%d')

        # 动态构建 SQL 查询
        union_queries = []
        params = []
        for feature in self.features:
            query = f"SELECT u.username, '{feature['feature']}' AS feature, COUNT(r.datetime) AS record_count, NULL AS datetime\n"
            if feature['type_id']:
                # 将日期条件和 type_id 移到 JOIN 子句中
                query += f"FROM user u\nLEFT JOIN {feature['table']} r ON u.username = r.user_id AND r.type_id = %s AND DATE(r.datetime) BETWEEN %s AND %s\n"
                params.extend([feature['type_id'], start_date, end_date])
            else:
                # 仅将日期条件移到 JOIN 子句中
                query += f"FROM user u\nLEFT JOIN {feature['table']} r ON u.username = r.user_id AND DATE(r.datetime) BETWEEN %s AND %s\n"
                params.extend([start_date, end_date])

            query += "GROUP BY u.username"
            union_queries.append(query)

        final_sql = " UNION ALL ".join(union_queries) + ";"

        try:
            self.db_handler.cursor.execute(final_sql, params)
            results = self.db_handler.cursor.fetchall()

            # 格式化结果
            formatted_results = {}

            for row in results:
                username = row['username']
                feature = row['feature']
                record_count = row['record_count']

                if username not in formatted_results:
                    # 初始化所有功能
                    formatted_results[username] = {
                        feature_entry['feature']: {'record_count': 0}
                        for feature_entry in self.features
                    }

                # 更新记录数
                formatted_results[username][feature]['record_count'] = record_count

            return formatted_results
        except Exception as e:
            print(f"An error occurred while querying user feature record count: {e}")
            return {}

record_count = UserFeatureRecordCount(db_handler)
