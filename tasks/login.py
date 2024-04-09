from model import User
import json
import os

CODE_SUCCESS = 0
CODE_ERROR = 1
USER = './assets/user/user.txt'


def login(username, password):
    if username is None or password is None:
        msg = '用户和密码不能为空'
        print(msg)
        return CODE_ERROR, None, msg
    user = User(username, password)
    if user.select():
        print(f"登录成功！欢迎, {username}")
        user_info = {"username": username, "password": password}
        with open(USER, 'w') as file:
            json.dump(user_info, file)
        return CODE_SUCCESS, username, None
    else:
        msg = "登录失败，用户名或密码错误。"
        print(msg)
        return CODE_ERROR, None, msg


def logout():
    try:
        # 检查文件是否存在
        if os.path.exists(USER):
            with open(USER, 'r') as f:
                user_info = json.load(f)
                # 获取并打印username
                username = user_info.get('username', 'Unknown')
            # 删除文件
            print(f"{username}退出")
            os.remove(USER)
            return CODE_SUCCESS, username, None
        else:
            msg = "用户不存在"
            print(msg)
            return CODE_SUCCESS, None, msg
    except Exception as e:
        print(f"登出过程中出现错误: {e}")
