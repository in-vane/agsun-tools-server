import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

SECRET_KEY = "your_secret_key_here"

def decode_jwt(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = decoded.get('sub')  # 'sub'字段包含了用户名
        return username
    except ExpiredSignatureError:
        return None  # 或者你可以抛出一个自定义异常
    except InvalidTokenError:
        return None  # 或者你可以抛出一个自定义异常
