from model import User
import jwt
from datetime import datetime, timezone, timedelta

CODE_SUCCESS = 0
CODE_ERROR = 1
SECRET_KEY = "your_secret_key_here"  # 你应该选择一个复杂的秘钥


def login(username, password):
    if username is None or password is None:
        msg = '用户和密码不能为空'
        print(msg)
        return CODE_ERROR, None, msg
    user = User(username, password)
    if user.select():
        # 登录成功，创建JWT
        payload = {
            'exp': datetime.now(timezone.utc) + timedelta(hours=12),   # 设置过期时间
            'iat': datetime.now(timezone.utc),  # 签发时间
            'sub': username  # 主题（这里用用户名）
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        print(f"登录成功！欢迎, {username}")
        return CODE_SUCCESS, token, f"登录成功！欢迎, {username}"
    else:
        print("登录失败，用户名或密码错误。")
        return CODE_ERROR, None, '登录失败，用户名或密码错误。'
