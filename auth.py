import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
SECRET_KEY = "your_secret_key_here"

def decode_jwt(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = decoded.get('sub')  # 'sub'字段包含了用户名
        return username
    except ExpiredSignatureError:
        print("token已经过期")
        try:
            # 解码Token，不验证过期时间，以提取用户名
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
            username = decoded.get('sub')
            # 延长过期时间，比如再延长1小时
            decoded['exp'] = datetime.utcnow() + timedelta(hours=1)
            return username
        except Exception as e:
            print(f"解码过期的Token时出错: {e}")
            return None
    except InvalidTokenError:
        print("Token无效")
        return None
