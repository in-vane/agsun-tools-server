import os
import shutil
import base64
import io
from PIL import Image
from io import BytesIO

import fitz
import pandas as pd
from tabula import read_pdf


PDF_PATH = './python/assets/pdf/temp.pdf'
CSV_PATH = './python/assets/csv/exact_table.csv' 
SUCCESS = 0
ERROR_NO_EXPLORED_VIEW = 1
BASE64_PNG = 'data:image/png;base64,'

"""
# 预测爆炸图的二分模型
class SimpleImageDataset(Dataset):
    def __init__(self, directory, transform=None):
        self.directory = Path(directory)
        self.transform = transform
        # List all png files in the directory
        self.image_paths = list(self.directory.glob('*.png'))

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')  # Convert to RGB for models expecting 3 channel inputs
        if self.transform:
            image = self.transform(image)
        return image
"""

# 对表格进行预处理，以纠正列名
def process_table(table):
    # 如果列名中含有'.1'，则移除
    corrected_columns = [col.split('.1')[0] if '.1' in col else col for col in table.columns]
    table.columns = corrected_columns
    return table


# 检查表格是否符合我们想要的格式
def is_desired_table(table):
    if table.shape[1] == 6:
        try:
            # 尝试将第一列和第四列转换为数值型，并检查它们是否按顺序递增
            first_col = pd.to_numeric(table.iloc[:, 0]).dropna()
            fourth_col = pd.to_numeric(table.iloc[:, 3]).dropna()
            # 检查列是否递增，列标题是否匹配
            if first_col.is_monotonic_increasing and fourth_col.is_monotonic_increasing:
                if table.columns[0] == table.columns[3] and \
                        table.columns[1] == table.columns[4] and \
                        table.columns[2] == table.columns[5]:
                    return True
        except ValueError:
            # 如果无法转换为数值型，那么这个表格不符合条件
            pass
    return False


# 读取PDF中的表格并进行筛选
def read_and_filter_tables(page_number):
    # 使用tabula读取指定页码的表格
    tables = read_pdf(PDF_PATH, pages=page_number, multiple_tables=True)

    # 处理每个表格的列名
    processed_tables = [process_table(table) for table in tables]

    # 筛选出符合条件的表格
    filtered_tables = [table for table in processed_tables if is_desired_table(table)]

    return filtered_tables

"""
# pdf转图片

def get_image(doc):
    # 确保输出目录存在
    if not os.path.isdir(IMAGE_PATH):
        os.makedirs(IMAGE_PATH)

    # 遍历PDF中的每一页
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)  # 读取页面
        pix = page.get_pixmap()  # 将页面转换为像素图
        output_image_path = os.path.join(IMAGE_PATH, f"page_{page_num + 1}.png")
        pix.save(output_image_path)  # 保存图像

# 预测是否为爆炸图
def predict():
    # Define the image transformations
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Initialize the model
    model = resnet18()
    num_ftrs = model.fc.in_features
    model.fc = Linear(num_ftrs, 2)  # Adjust to match the number of classes you have
    model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
    model.eval()

    # Load the image dataset
    dataset = SimpleImageDataset(directory=IMAGE_PATH, transform=transform)
    loader = DataLoader(dataset, batch_size=1, shuffle=False)
    result = {}

    # Iterate over the dataset and make predictions
    for img_tensor, img_path in zip(loader, dataset.image_paths):
        with torch.no_grad():
            outputs = model(img_tensor)
            _, preds = torch.max(outputs, 1)
            # Extract the image file name from the image path
            img_name = os.path.basename(img_path)
            if preds.item() == 1:
                page_number = img_name.split('_')[1].split('.')[0]
                result[page_number] = img_name

    return result
"""

# 标注错误
def add_annotation_with_fitz(doc, annotations):
    for page_number, texts in annotations.items():
        # 获取页面对象
        page = doc[page_number - 1]  # 页面索引从0开始

        # 定义左上角区域的矩形，例如：30像素从左边界，30像素从顶部边界，宽度为页面宽度的一半，高度为50像素
        top_left_rect = fitz.Rect(30, 30, page.rect.width / 2, 80)

        # 在左上角区域添加红色文本
        page.insert_textbox(top_left_rect, texts, color=fitz.utils.getColor("red"), fontsize=12,
                            align=fitz.TEXT_ALIGN_LEFT)


# 转换字典中的浮点数为整数
def convert_values_to_int(d):
    new_dict = {}
    for k, v in d.items():
        # 转换键
        if isinstance(k, float) or (isinstance(k, str) and k.isdigit()):
            new_key = int(k)
        else:
            new_key = k

        # 转换值
        if isinstance(v, float) or (isinstance(v, str) and v.isdigit()):
            new_value = int(v)
        else:
            new_value = v

        new_dict[new_key] = new_value

    return new_dict


# 比较表格检查错误
def compare_tables_with_csv(table):
    # 读取CSV文件并创建字典
    csv_table = pd.read_csv(CSV_PATH)
    csv_dict = pd.Series(csv_table.iloc[:, 2].values, index=csv_table.iloc[:, 0]).to_dict()
    csv_dict.update(pd.Series(csv_table.iloc[:, 5].values, index=csv_table.iloc[:, 3]).to_dict())

    # 转换字典中的浮点数为整数
    csv_dict = convert_values_to_int(csv_dict)

    # 将传入的DataFrame转换成字典
    pdf_dict = pd.Series(table.iloc[:, 2].values, index=table.iloc[:, 0]).to_dict()
    pdf_dict.update(pd.Series(table.iloc[:, 5].values, index=table.iloc[:, 3]).to_dict())

    # 转换字典中的浮点数为整数
    pdf_dict = convert_values_to_int(pdf_dict)

    # 比较两个字典
    mismatch = False
    mismatch_number = []
    for key in csv_dict:
        if key in pdf_dict and csv_dict[key] != pdf_dict[key]:
            print(f"不匹配的序号：{key}")
            mismatch = True
            mismatch_number.append(key)

    return mismatch, mismatch_number


# 查找匹配的表格
def find_matching_table(doc, exact_pagenumber, table_character, ):
    if len(table_character) != 2:
        print("Error: 'table_character' should be a list with two elements: [number_of_rows, number_of_columns]")
        return None

    num_rows, num_columns = table_character
    count = 0
    mismatched_pages = []  # 存储不匹配的页号
    page_exact_number = exact_pagenumber + 1
    page_count = len(doc)
    total_mismatch_number = {}
    for page_number in range(page_exact_number, page_count):
        # 读取当前页的表格
        tables = read_pdf(PDF_PATH, pages=page_number, multiple_tables=True)

        for table in tables:
            # 检查表格行数和列数是否符合要求
            if table.shape[0] == num_rows and table.shape[1] == num_columns:
                count += 1
                # 检查表格与CSV是否匹配
                is_mismatched, mismatch_number = compare_tables_with_csv(table)
                if is_mismatched:
                    mismatched_pages.append(page_number)
                    total_mismatch_number[page_number] = mismatch_number
                print(f"Found a matching table on page {page_number}")
            # 如果检测到的表格行数比预期多一行，则删除第一行
            if table.shape[0] == num_rows + 1 and table.shape[1] == num_columns:
                table = table.drop(table.index[0]).reset_index(drop=True)
                count += 1
                # 检查表格与CSV是否匹配
                is_mismatched, mismatch_number = compare_tables_with_csv(table)
                if is_mismatched:
                    mismatched_pages.append(page_number)
                    total_mismatch_number[page_number] = mismatch_number
                print(f"Found a matching table on page {page_number}")

    print(f"相似表格个数:{count}")
    print(f"不匹配的页数：{mismatched_pages}")
    print(f"不匹配的页数和对应的表格序号{total_mismatch_number}")

    # 创建注释字典
    annotations = {}
    for page in mismatched_pages:
        if page in total_mismatch_number:
            mismatch_info = f"mismatch: {total_mismatch_number[page]}"
            annotations[page] = mismatch_info
    add_annotation_with_fitz(doc, annotations)

    return mismatched_pages


def get_error_pages_as_base64(error_pages, doc):
    """
    将PDF中指定的错误页转换为图片，获取其字节流并转化为base64字符串。

    :param error_pages: 包含错误页页码的列表，页码从1开始。
    :param doc: fitz.Document对象
    :return: 包含每个错误页面图片Base64字符串的列表
    """
    base64_images = []

    for page_num in error_pages:
        page_index = page_num - 1
        page = doc.load_page(page_index)
        pix = page.get_pixmap()
        # 使用pixmap的samples属性来获取像素数据
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")  # 使用Pillow保存图像数据到BytesIO对象
        img_bytes.seek(0)

        base64_str = base64.b64encode(img_bytes.read()).decode('utf-8')
        base64_images.append(f"{BASE64_PNG}{base64_str}")

    return base64_images


# 主函数
def compare_table(file, page_number):
    # 打开PDF文件
    # doc =fitz.open(file)
    doc = fitz.open(stream=BytesIO(file))
    doc.save(PDF_PATH)
    # 获取标准表格
    filtered_tables = read_and_filter_tables(page_number)
    if filtered_tables:
        print("在该页找到标准表格了")
    else:
        print("在该页没找到标准表格了")


    # 假设 filtered_tables 是之前从 PDF 中提取并筛选出的表格列表
    # 下面的代码会遍历这些表格，打印出它们的行数和列数，并将它们存储为 CSV 文件
    table_character = []
    for i, table in enumerate(filtered_tables):
        print(f"Table {i + 1}:")
        print(f"Number of rows: {table.shape[0]}")
        print(f"Number of columns: {table.shape[1]}")
        table_character.append(table.shape[0])
        table_character.append(table.shape[1])
        table.to_csv(CSV_PATH, index=False)



    error_pages = find_matching_table(doc, page_number, table_character)
    images_base64 = get_error_pages_as_base64(error_pages, doc)

    # 将文档转换成字节流
    # doc_bytes = doc.write()
    # 将字节流进行base64编码
    # doc_base64 = base64.b64encode(doc_bytes).decode('utf-8')

    doc.close()
    os.remove(PDF_PATH)
    os.remove(CSV_PATH)
    # shutil.rmtree(IMAGE_PATH)

    return images_base64, error_pages
# 测试接口
# compare_table('1.pdf',2)