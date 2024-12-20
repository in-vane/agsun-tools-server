from io import BytesIO
from PIL import Image
import base64
import fitz
import re
import os

from logger import logger
from save_filesys_db import save_Page_number

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor

CODE_SUCCESS = 0
CODE_ERROR = 1


def annotate_page_number_issues(doc, physical_page_numbers, issues):
    # 检查页码问题
    error_pages_base64 = []

    # 在有问题的页面上添加注释
    for issue_page_num in issues:
        # 找到对应的物理页码
        physical_page_index = physical_page_numbers[issue_page_num - 1]
        page = doc.load_page(physical_page_index - 1)
        footer_rect = fitz.Rect(0, page.rect.height -
                                50, page.rect.width, page.rect.height)

        # 在页脚区域添加红色文本
        align = fitz.TEXT_ALIGN_LEFT if issue_page_num % 2 == 0 else fitz.TEXT_ALIGN_RIGHT
        page.insert_textbox(footer_rect, "Page error", color=fitz.utils.getColor(
            "red"), fontsize=12, align=align)

        # 将页面转换为图像
        pix = page.get_pixmap(alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 将图像转换为base64编码
        buffer = BytesIO()
        img.save(buffer, format="JPEG")  # 可以选择PNG或者JPEG格式
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        buffer.close()
        error_pages_base64.append(f"data:image/jpeg;base64,{img_base64}")

    return error_pages_base64


def check_page_number_issues(printed_page_numbers, physical_page_numbers, start, end):
    if start != -1 and end != -1:
        # 确保 start 和 end 的值在有效范围内
        start = max(1, start)  # 保证start不小于1
        end = min(len(printed_page_numbers), end)  # 保证end不大于列表长度
        # 将 start 和 end 调整为从0开始的索引
        start_index = start - 1
        end_index = end
        printed_page_numbers = printed_page_numbers[start_index:end_index]
        physical_page_numbers = physical_page_numbers[start_index:end_index]
    printed = printed_page_numbers
    issues = []  # 初始化问题列表
    start_index = None  # 找到第一个非None打印页码的索引
    correct_page_numbers = printed_page_numbers.copy()  # 创建正确页码的副本以进行修改

    # 查找第一个非None打印页码的索引
    for index, page_number in enumerate(printed_page_numbers):
        if page_number is not None:
            start_index = index
            break

    # 如果找到了有效的起始页码
    if start_index is not None:
        # 生成从第一个有效数字开始的连续页码序列
        expected_number = printed_page_numbers[start_index]
        for i in range(start_index, len(printed_page_numbers)):
            correct_page_numbers[i] = expected_number
            expected_number += 1

    # 比较实际页码与正确页码，记录不一致的物理页码
    for i in range(len(printed_page_numbers)):
        if printed_page_numbers[i] != correct_page_numbers[i]:
            issues.append(physical_page_numbers[i])

    return issues, printed


def extract_page_numbers(doc, rect):
    printed_page_numbers = []  # 初始化打印页码列表
    total_pages = len(doc)  # 获取PDF的总页数

    for page_num in range(total_pages):
        page = doc.load_page(page_num)  # 加载当前页

        if rect in ([0.0, 0.0, 0.0, 0.0], [0, 0, 0, 0]):
            # 如果 rect 为 [0.0, 0.0, 0.0, 0.0]，则重新定义页脚区域
            page_width = page.rect.width
            page_height = page.rect.height

            footer_rect = fitz.Rect(0.0, page_height - 65, page_width, page_height)
        else:
            # 使用传入的 rect 参数定义页脚区域
            footer_rect = fitz.Rect(rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])

        # 从页脚区域提取文本
        footer_text = page.get_text("text", clip=footer_rect)

        # 使用正则表达式查找所有数字
        numbers = re.findall(r'\d+', footer_text)

        # 在页脚区域添加红色边框
        page.draw_rect(footer_rect, color=(1, 0, 0), width=1.5)
        # 如果当前页页脚区域有数字，则假设最大的数字是页码
        if numbers:
            probable_page_number = ''.join(reversed(numbers))
        else:
            # 如果没有找到数字，将None添加到列表中
            probable_page_number = None

        printed_page_numbers.append(probable_page_number)

    # 将打印页码列表中的元素转换为整数，对于None值保持不变
    printed_page_numbers = [
        int(item) if item is not None else None for item in printed_page_numbers]

    return printed_page_numbers


# 主函数
def check_page_number(username, file, filename, rect, start, end):
    logger.info("---begin check_page_number---")
    print(username, file, filename, rect)
    logger.info(f"username : {username}")
    if not file:
        msg = '文件损坏或者为空文件'
        logger.info(msg)
        return CODE_ERROR, None, msg
    doc = fitz.open(file)
    if end == -1:
        end = len(doc)
    # 生成物理页码列表，从1开始到总页数
    physical_page_numbers = list(range(1, len(doc) + 1))
    logger.info(f"physical_page_numbers:{physical_page_numbers}")
    # 获取文件中的页码表
    printed_page_numbers = extract_page_numbers(doc,rect)
    logger.info(f"printed_page_numbers:{printed_page_numbers}")
    # 对比两个页码表
    issues, printed = check_page_number_issues(
        printed_page_numbers, physical_page_numbers, start, end)
    is_error = False if len(issues) == 0 else True
    # 在错误的页码附近标注错误
    # 检查列表中的所有元素是否都是 None
    if all(x is None for x in printed_page_numbers):
        note = '区域里未检测到数字页码，请检查是否有页码，页码是否为文字'
    elif is_error == True:
        note = f'页码错误,{printed}'
    else:
        note = f'页码无误,{printed}'
    error_pages_base64 = annotate_page_number_issues(
        doc, physical_page_numbers, issues)
    logger.info(f"error page number:{issues}")
    logger.info("save file")
    save_Page_number(username['username'], CODE_SUCCESS, file, is_error, issues, note, error_pages_base64, '')
    logger.info("save success")
    doc.close()
    logger.info("---end check_page_number---")
    return CODE_SUCCESS, is_error, issues, error_pages_base64, note, None


class PageNumberHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file, filename, rect, start, end):
        return check_page_number(username, file, filename, rect, start, end)
    async def post(self):
        username = self.current_user
        params = tornado.escape.json_decode(self.request.body)
        print(f"传入参数为:{params}")
        file = params['file_path']
        rect = params['rect']
        rect = [value * 72 / 300 for value in rect]
        filename = os.path.basename(file)
        start = int(params.get('start', -1))
        end = int(params.get('end', -1))
        code, error, error_page, result, note, msg = await self.process_async(username,
                                                                          file, filename, rect,start, end)
        custom_data = {
            'code': code,
            'data': {
                "error": error,
                "error_page": error_page,
                "note": note,
                "result": result
            },
            'msg': msg

        }
        self.write(custom_data)