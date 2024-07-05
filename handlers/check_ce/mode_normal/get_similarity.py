import re
from sentence_transformers import SentenceTransformer, util
import requests
import hashlib
from langdetect import detect
from config import MiniLM_PATH, app_id, secret_key
def compute_cosine_similarity(text1, text2):
    """
    该函数为了，计算两个句子的语义相似度,比如'你好'和'hello'，会先把两个都翻译成英语
    再计算其相似度
    :param text1:
    :param text2:
    :return: 相似度数值，0到1的数值
    """
    model = SentenceTransformer(MiniLM_PATH)
    sentences = []
    sentences.append(text1)
    sentences.append(text2)
    # Generate embeddings
    embeddings = model.encode(sentences)

    # 计算相似度
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity

def clean_string(s):
    """忽略大小写、空格、符号和回车符号的比较"""
    # 移除所有非字母数字字符，包括空格、标点符号、回车符和换行符
    cleaned = re.sub(r'\W+', '', s.replace('\n', '').replace('\r', '')).strip().lower()
    return cleaned
def compare_lists(list1, list2):
    """对两个列表的值进行比较，忽略大小写、空格和符号，并返回不匹配的索引列表"""
    mismatched_indices = []
    for index, (item1, item2) in enumerate(zip(list1, list2)):
        if clean_string(item1) != clean_string(item2):
            mismatched_indices.append(index + 1)  # 索引从1开始
    return mismatched_indices

def compare_dictionaries(red_text_data, table_data):
    """
    比较两个字典的键和值，忽略大小写、空格和符号的比较。
    :param red_text_data: 吉盛标准ce表读入后的字典
    :param table_data: 客户修改版本，读入的字典
    :return: 差异字典
    """
    # 创建副本
    red_text_data_copy = red_text_data.copy()
    table_data_copy = table_data.copy()

    # 翻译客户修改版本的字典键
    table_data_copy = baidu_translate(table_data_copy)
    # 初始化差异字典
    message_dict = {}
    print("--开始键相等对比--")

    # 存储需要删除的键
    red_keys_to_remove = []
    table_keys_to_remove = []

    # 比较两个字典的键
    for red_key in list(red_text_data_copy.keys()):
        matched = False
        for table_key in list(table_data_copy.keys()):
            # 如果键相等，忽略大小写、空格和符号
            if clean_string(red_key) == clean_string(table_key):
                print(f"{red_key}与{table_key}其键相同")
                matched = True
                # 如果键对应的值长度不同，记录差异
                if len(red_text_data_copy[red_key]) != len(table_data_copy[table_key]):
                    print(f"{red_text_data_copy[red_key]}与{table_data_copy[table_key]}长度不同")
                    message_dict[red_key] = list(range(1, len(red_text_data_copy[red_key]) + 1))
                else:
                    # 如果键对应的值长度相同但内容不同，记录差异
                    mismatched_indices = compare_lists(red_text_data_copy[red_key], table_data_copy[table_key])
                    if mismatched_indices:
                        print(f"{red_text_data_copy[red_key]}与{table_data_copy[table_key]}值不相同")
                        message_dict[red_key] = mismatched_indices

                # 无论是否匹配到相同的值，删除键值对
                red_keys_to_remove.append(red_key)
                table_keys_to_remove.append(table_key)
                break

    # 删除已经匹配的键
    for red_key in red_keys_to_remove:
        del red_text_data_copy[red_key]
    for table_key in table_keys_to_remove:
        del table_data_copy[table_key]

    print(f"--没匹配到:{red_text_data_copy}开始值相等对比--")
    # 对剩余的键进行值列表长度相同的比较
    red_keys_to_remove = []

    for red_key in list(red_text_data_copy.keys()):
        for table_key in list(table_data_copy.keys()):
            # 如果值列表长度相同且内容相同，忽略大小写、空格和符号
            if len(red_text_data_copy[red_key]) == len(table_data_copy[table_key]):
                mismatched_indices = compare_lists(red_text_data_copy[red_key], table_data_copy[table_key])
                if not mismatched_indices:
                    print(f"{red_text_data_copy[red_key]}与{table_data_copy[table_key]}值相同")
                    red_keys_to_remove.append(red_key)
                    break

    # 删除已经匹配的键
    for red_key in red_keys_to_remove:
        del red_text_data_copy[red_key]

    # 对剩余的键进行语义相似度比较
    print(f"--没匹配到:{red_text_data_copy}开始键语义对比--")


    for red_key in list(red_text_data_copy.keys()):
        max_similarity = 0
        most_similar_key = None

        # 找到与 red_key 最相似的 table_key
        for table_key in list(table_data_copy.keys()):
            similarity = compute_cosine_similarity(red_key, table_key)
            if similarity == 1:
                max_similarity = 1
                most_similar_key = table_key
                break
            elif similarity > max_similarity:
                max_similarity = similarity
                most_similar_key = table_key

        # 检查最相似的键是否达到相似度阈值
        if max_similarity >= 0.8:
            if len(red_text_data_copy[red_key]) != len(table_data_copy[most_similar_key]):
                message_dict[red_key] = list(range(1, len(red_text_data_copy[red_key]) + 1))
            else:
                mismatched_indices = compare_lists(red_text_data_copy[red_key], table_data_copy[most_similar_key])
                del table_data_copy[most_similar_key]
                del red_text_data_copy[red_key]
                if mismatched_indices:
                    message_dict[red_key] = mismatched_indices
        else:
            message_dict[red_key] = list(range(1, len(red_text_data_copy[red_key]) + 1))

    # 检查是否还有键值对，如果有，则加入message_dict
    for red_key in list(red_text_data_copy.keys()):
        message_dict[red_key] = list(range(1, len(red_text_data_copy[red_key]) + 1))

    # 检查message_dict是否有键'CE-sign'
    if 'CE-sign' in message_dict:
        if 'CE-sign' in red_text_data and 'CE-sign' in table_data:
            red_ce_values = red_text_data['CE-sign']
            table_ce_values = table_data['CE-sign']
            if all(any(clean_string(value1) == clean_string(value2) for value2 in table_ce_values) for value1 in
                   red_ce_values):
                del message_dict['CE-sign']
            else:
                message_dict['CE-sign'] = red_text_data['CE-sign']

    print(f"最终的对比结果{message_dict}")
    return message_dict

def baidu_translate(data_dict, app_id=app_id, secret_key=secret_key, from_lang='auto', to_lang='en'):
    translated_dict = {}
    base_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = '123456'

    for key, value in data_dict.items():
        sign_str = app_id + key + salt + secret_key
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        params = {
            'q': key,
            'appid': app_id,
            'salt': salt,
            'from': from_lang,
            'to': to_lang,
            'sign': sign
        }

        response = requests.get(base_url, params=params)
        result = response.json()

        if "trans_result" in result:
            translated_key = result["trans_result"][0]["dst"]
            translated_dict[translated_key] = value
        else:
            translated_dict[key] = value  # 使用原始键如果翻译失败
    print(f"翻译后的字典为:{translated_dict}")
    return translated_dict

# 测试上面函数
# red_text_data = {'CE-sign': ['2575-24'], 'Model Number': ['K103M1EGM2'], 'Product Identification Number': ['2575XXXXXXX'], 'Main Burner Injector Size': ['Ø 0.92mm', 'Ø 0.92mm', 'Ø 0.86mm', 'Ø 0.81mm'], 'Side Burner Injector Size ': ['Ø 0.88mm', 'Ø 0.88mm', 'Ø 0.79mm', 'Ø 0.75mm'], 'Side Burner （infrared）Injector Size ': ['Ø 0.92mm', 'Ø 0.92mm', 'Ø 0.86mm', 'Ø 0.81mm'], 'Infrared Burner Injector Size ': ['Ø 0.91mm', 'Ø 0.91mm', 'Ø 0.83mm', 'Ø 0.79mm'], 'Total Nominal Heat Inputs (Hs)': ['Main 13.5kW(983g/h ) ；'], 'Electric energy': ['5×1.5V']}
# table_data = {'Product name': ['Outdoor gas grill'], 'Model number': ['Cliff 3500 Beast(K103M1BEGM2)'], 'Gas category': ['I3+(28-30/37)', 'I3B/P(30)', 'I3B/P(37)', 'I3B/P(50)'], 'Gas and supply pressure': ['Butane (G30)', 'Propane (G31)', 'Butane/Propane'], 'Country of destination': ['I3+(28-30/37): BE, CH, CY, CZ, ES, FR, GB, GR, IE, IT, LT, LU, LV, PT, SK, SI, TR\\nI3B/P(30): AL, CY, CZ, DK, EE, FI, FR, HU, IT, LT, NL, NO, RO, SE, SI, SK, HR, TR, BG, IS, LU, MT, MK, GB, GR, LV, IS\\nI3B/P(50): AT, CH, CZ, DE, SK, LU\\nI3B/P(37): PL'], 'Main burner injector size': ['Ø 0.92 mm', 'Ø 0.92 mm', 'Ø 0.92 mm', 'Ø 0.86 mm', 'Ø 0.81 mm'], 'Side burner injector size': ['Ø 0.88 mm', 'Ø 0.88 mm', 'Ø 0.88 mm', 'Ø 0.79 mm', 'Ø 0.75 mm'], 'Total output:': ['13,5 kW / 983 (g/h)'], 'Electric energy(V / DC)': ['–'], 'Serial number': ['Can be found on the right side of the fire box'], 'Use outdoors only': [], 'Read the instructions before using the appliance.': [], 'Warning : Accessible parts may be very hot. Keep young children away. Made in China': [], 'CE-sign': ['2575-24']}
# compare_dictionaries(red_text_data, table_data)
