import os
from sentence_transformers import SentenceTransformer, util
import requests
import hashlib
from langdetect import detect


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
MiniLM_PATH = os.path.join(CURRENT_PATH, "all-MiniLM-L6-v2")

def compute_cosine_similarity(text1, text2):
    """
    该函数为了，计算两个句子的语义相似度,比如'你好'和'hello'，会先把两个都翻译成英语
    再计算其相似度
    :param text1:
    :param text2:
    :return: 相似度数值，0到1的数值
    """
    # 将两个句子翻译成英文
    translated_sentence1 = baidu_translate(text1)
    translated_sentence2 = baidu_translate(text2)
    # 判断语义相似度的模型
    model = SentenceTransformer(MiniLM_PATH)
    sentences = []
    sentences.append(translated_sentence1)
    sentences.append(translated_sentence2)
    # Generate embeddings
    embeddings = model.encode(sentences)

    # 计算相似度
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity


def compare_values_containment(list1, list2):
    """
    逐个对比两个长度相同的列表，考虑到因不同输入法导致的字符差异，
    对字符串进行预处理后再进行比较。
    :param list1: 标准列表
    :param list2: 对比列表
    :return: 匹配成功返回空列表，匹配失败返回不匹配值的索引列表
    """
    mismatch = []

    # 定义替换规则
    replace_rules = {
        "；": ";", "，": ",", "。": ".", "：": ":", "（": "(", "）": ")",
        "【": "[", "】": "]", "｛": "{", "｝": "}", "？": "?", "！": "!"
    }

    for index, (value1, value2) in enumerate(zip(list1, list2), start=1):
        # 应用所有替换规则
        for old, new in replace_rules.items():
            value1 = value1.replace(old, new)
            value2 = value2.replace(old, new)

        # 比较处理后的字符串
        if value1 != value2:
            mismatch.append(index)

    return mismatch


def compare_dictionaries(red_text_data, table_data):
    """
    该方法将red_text_data的键，与table_data的键，相互语义比较相似度，得到
    多个相似度，在这多相似度取最大值.
    if最大值>=0.8:
         if 该键与最大值的键，两个键所对应的值(值是列表),判断列表长度是否一样:
            再进行逐个对比列表中的值
         else:
            键的值长度不同
    else:
         该红色字体对应的键，对于客户ce表，未找到匹配

    :param red_text_data: 吉盛标准ce表读入后的字典
    :param table_data: 客户修改版本，读入的字典
    :return:
    """
    message_dict = {}
    for red_key in red_text_data.keys():
        max_similarity = 0
        most_similar_key = None

        # 比较red_key与table_data中的每个键
        for table_key in table_data.keys():
            similarity = compute_cosine_similarity(red_key, table_key)
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_key = table_key

        # 检查最相似的键
        if max_similarity >= 0.8:
            if len(red_text_data[red_key]) != len(table_data[most_similar_key]):
                print(max_similarity)
                print(f"键的值长度不同: {red_key}")
                message_dict[red_key] = list(range(1, len(red_text_data[red_key]) + 1))
            else:
                # 如果数量相同，则比较列表里的值
                print(max_similarity)
                mismatch = compare_values_containment(red_text_data[red_key], table_data[most_similar_key])
                if mismatch:
                    message_dict[red_key] = mismatch
                    print(f"值有差异: {red_key}")
                else:
                    print(f"相似匹配成功: {red_key} 匹配的键为{most_similar_key}")
        else:
            print(max_similarity)
            print(f"相似度小于0.8: {red_key}")
            message_dict[red_key] = list(range(1, len(red_text_data[red_key]) + 1))
    # 假设message_dict是你的字典变量
    if "CE-sign" in message_dict:
        message_dict['CE-sign'] = red_text_data['CE-sign']

    return message_dict


def baidu_translate(query, app_id='20240303001981368', secret_key='0_Nq4RdREx1L31eWiDbr', from_lang='auto',
                    to_lang='en'):
    """
    用百度翻译平台，把传过来的句子，翻译成英语
    :param query: 传进来要翻译的句子
    :param app_id: 百度翻译的id
    :param secret_key: 百度翻译的密码
    :param from_lang:
    :param to_lang: 英语
    :return: 翻译好的句子
    """
    if isinstance(query, str):
        query = query.strip()
        if not query:
            print("Empty string detected.")
            return query

        try:
            detected_lang = detect(query)
            # print(f"Detected language: {detected_lang}")
        except Exception as e:
            print(f"Error in language detection: {str(e)}")
            return f"Error in language detection: {str(e)}"

        if detected_lang == 'en':
            return query

        base_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        salt = '123456'
        sign_str = app_id + query + salt + secret_key
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        params = {'q': query, 'appid': app_id, 'salt': salt, 'from': from_lang, 'to': to_lang, 'sign': sign}

        response = requests.get(base_url, params=params)
        result = response.json()

        # print(f"Translation API response: {result}")

        if "trans_result" in result:
            return result["trans_result"][0]["dst"]
        else:
            print("Error: Unable to translate")
            return "Error: Unable to translate"
    else:
        # print("Input is not a string.")
        return "Input is not a string"

# 测试上面函数
# red_text_data = {'CE-sign': ['2575-24'], 'Model Number': ['K103M1EGM2'], 'Product Identification Number': ['2575XXXXXXX'], 'Main Burner Injector Size': ['Ø 0.92mm', 'Ø 0.92mm', 'Ø 0.86mm', 'Ø 0.81mm'], 'Side Burner Injector Size ': ['Ø 0.88mm', 'Ø 0.88mm', 'Ø 0.79mm', 'Ø 0.75mm'], 'Side Burner （infrared）Injector Size ': ['Ø 0.92mm', 'Ø 0.92mm', 'Ø 0.86mm', 'Ø 0.81mm'], 'Infrared Burner Injector Size ': ['Ø 0.91mm', 'Ø 0.91mm', 'Ø 0.83mm', 'Ø 0.79mm'], 'Total Nominal Heat Inputs (Hs)': ['Main 13.5kW(983g/h ) ；'], 'Electric energy': ['5×1.5V']}

# table_data = {'Product name': ['Outdoor gas grill'], 'Model number': ['Cliff 3500 Beast(K103M1BEGM2)'], 'Gas category': ['I3+(28-30/37)', 'I3B/P(30)', 'I3B/P(37)', 'I3B/P(50)'], 'Gas and supply pressure': ['Butane (G30)', 'Propane (G31)', 'Butane/Propane'], 'Country of destination': ['I3+(28-30/37): BE, CH, CY, CZ, ES, FR, GB, GR, IE, IT, LT, LU, LV, PT, SK, SI, TR\\nI3B/P(30): AL, CY, CZ, DK, EE, FI, FR, HU, IT, LT, NL, NO, RO, SE, SI, SK, HR, TR, BG, IS, LU, MT, MK, GB, GR, LV, IS\\nI3B/P(50): AT, CH, CZ, DE, SK, LU\\nI3B/P(37): PL'], 'Main burner injector size': ['Ø 0.92 mm', 'Ø 0.92 mm', 'Ø 0.92 mm', 'Ø 0.86 mm', 'Ø 0.81 mm'], 'Side burner injector size': ['Ø 0.88 mm', 'Ø 0.88 mm', 'Ø 0.88 mm', 'Ø 0.79 mm', 'Ø 0.75 mm'], 'Total output:': ['13,5 kW / 983 (g/h)'], 'Electric energy(V / DC)': ['–'], 'Serial number': ['Can be found on the right side of the fire box'], 'Use outdoors only': [], 'Read the instructions before using the appliance.': [], 'Warning : Accessible parts may be very hot. Keep young children away. Made in China': [], 'CE-sign': ['2575-24']}

# compare_dictionaries(red_text_data, table_data)
