import os
import base64
from io import BytesIO
import io
from PIL import Image
import fitz
import jpype
import openpyxl
from openpyxl.styles import Border, Side

from .get_table_message import all

EXCEL_PATH = './python/assets/excel/temp.xlsx'
IMAGE_PATH = './python/assets/images/temp.png'
PDF_PATH_FROM_EXCEL = './python/assets/pdf/temp_excel.pdf'
PDF_PATH = './python/assets/pdf/temp.pdf'


def change_excel(wb, work_table, message_dict):
    """
    该函数主要是为了，呈现错误信息到吉盛标准ce表上
    :param excel: 吉森标准ce表
    :param work_table: ce表中的工作表
    :param message_dict: 错误信息
    :return:
    """
    # 加载工作簿并选择工作表
    # wb = load_workbook(excel)
    sheet = wb[work_table]

    # 用绿色定义边框样式
    # 用绿色定义边框样式
    green_border = Border(
        left=Side(style='thick', color='0000FF'),
        right=Side(style='thick', color='0000FF'),
        top=Side(style='thick', color='0000FF'),
        bottom=Side(style='thick', color='0000FF')
    )

    # 如果message_dict中有'CE-sign'键，处理它的值
    if 'CE-sign' in message_dict:
        ce_values = message_dict['CE-sign']  # 获取'CE-sign'对应的值列表
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value in ce_values:  # 如果单元格的值在ce_values列表中
                    cell.border = green_border  # 更新边框为绿色

    # 遍历工作表中的每一行，更新其他指定的值的边框
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value in message_dict and cell.value != 'CE-sign':  # 排除'CE-sign'键
                red_texts_positions = message_dict[cell.value]  # 获取红色文本位置的列表
                red_texts_count = 0  # 找到的红色文本单元格的计数器

                for row_cell in row:
                    # 检查单元格的字体是否为红色
                    if row_cell.font and row_cell.font.color and row_cell.font.color.type == 'rgb' and row_cell.font.color.value == 'FFFF0000':
                        red_texts_count += 1  # 递增计数器
                        # 如果当前计数在位置列表中，则更新边界
                        if red_texts_count in red_texts_positions:
                            row_cell.border = green_border

    # 保存文件
    # wb.save(EXCEL_PATH)


# 将ecxel转化pdf
def convert_excel_sheet_to_pdf(excel_file, sheet_name):
    # 启动JVM
    if not jpype.isJVMStarted():
        jpype.startJVM()
    from asposecells.api import Workbook, PdfSaveOptions

    # 加载Excel文档
    workbook = Workbook(excel_file)

    # 获取所有工作表的集合
    worksheets = workbook.getWorksheets()

    # 遍历所有工作表
    for sheet in worksheets:
        print(f"excel中的工作表{sheet}")
        # 如果工作表不是要转换的工作表，将其隐藏
        if sheet.getName() != sheet_name:
            sheet.setVisible(False)

    # 设置PDF保存选项
    saveOptions = PdfSaveOptions()
    saveOptions.setOnePagePerSheet(True)

    # 保存为PDF
    workbook.save(PDF_PATH_FROM_EXCEL, saveOptions)

    # 关闭JVM
    jpype.shutdownJVM()

# 将pdf的第一页转化图片
def convert_pdf_page_to_image_base64(page_number=0):
    """
    Convert the specified page of a PDF file into a Base64 image string.
    :param pdf_path: Path to the PDF file.
    :param page_number: The number of the page to convert (0-based).
    :return: Base64 encoded string of the image.
    """
    # 打开PDF文件
    doc = fitz.open(PDF_PATH_FROM_EXCEL)

    # 选择PDF的指定页
    page = doc.load_page(page_number)

    # 将选中的页面转换为图片（pix）
    pix = page.get_pixmap()

     # 使用pixmap的samples属性来获取像素数据
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")  # 使用Pillow保存图像数据到BytesIO对象
    img_bytes.seek(0)

    base64_str = base64.b64encode(img_bytes.read()).decode('utf-8')

    # 关闭文档
    doc.close()

    return base64_str


def checkTags(excel_file, pdf_file):
    work_table = '例2'
    doc = fitz.open(stream=BytesIO(pdf_file))
    doc.save(PDF_PATH)
    wb = openpyxl.load_workbook(filename=BytesIO(excel_file))
    wb.save(EXCEL_PATH)
    message_dict = all(wb, work_table, doc, PDF_PATH)
    change_excel(wb, work_table, message_dict)
    # 将excel转化为pdf，保存到PDF_PATH
    convert_excel_sheet_to_pdf(EXCEL_PATH, work_table)
    # 将excel转化为pdf，保存到PDF_PATG
    image_base64 = convert_pdf_page_to_image_base64()


    os.remove(EXCEL_PATH)

    return image_base64


# checkTags('2.xlsx','2.pdf')