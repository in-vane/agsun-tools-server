import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

SECRET_KEY = "your_secret_key_here"
MOCK_TOKEN = 'eyJ1c2VybmFtZSI6ImFkbWluIiwicGFzc3dvcmQiOiJhZG1pbiIsImFsZyI6IkhTMjU2In0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.siWUAvcuC7TtFJIAW1qX4CMbPNpg92eeZ3SKDilNNGE'


def decode_jwt(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = decoded.get('sub')  # 'sub'字段包含了用户名
        return username
    except ExpiredSignatureError:
        return None  # 自定义异常
    except InvalidTokenError:
        return None  # 自定义异常
