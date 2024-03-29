import os
import fitz  # PyMuPDF
import cv2
import base64
from io import BytesIO
from skimage.metrics import structural_similarity as compare_ssim



# 新版pdf转化为图片文件夹
PDF1_IMAGE = './assets/image1'

# 旧版pdf转化为图片文件夹
PDF2_IMAGE = './assets/image2'
# 对比结果图片文件夹
RESULT_IMAGE = './assets/image3'
similarity_list = []

# pdf转化为图片，放入output_folder文件夹下
def pdf_to_images(doc, output_folder):
    """使用fitz（PyMuPDF）将PDF转换为图片，并保存到指定文件夹"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)  # 如果输出文件夹不存在，则创建
    for page_num, page in enumerate(doc, start=1):
        # 获取页面的Pixmap对象，这是一个图像对象
        pix = page.get_pixmap()
        img_path = os.path.join(output_folder, f"page_{page_num}.png")
        pix.save(img_path)  # 直接使用Pixmap对象的save方法保存图片
# 清空image1、image2和image3文件夹
def clear_directory_contents(dir_paths):
    """清空指定目录下的所有文件（不删除子目录中的内容）"""
    for dir_path in dir_paths:
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # 删除文件或链接
                elif os.path.isdir(file_path):
                    # 如果需要删除目录（及目录下所有内容），可以取消下面注释的代码
                    # shutil.rmtree(file_path)
                    pass
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
# 根据列表获取image3下的图片，再转化为base64
def images_to_base64_list(image_folder, page_numbers):
    """根据页号列表，将对应的图片转换为Base64字符串列表"""
    base64_strings = []
    for page_number in page_numbers:
        image_path = os.path.join(image_folder, f"page_{page_number}.png")
        with open(image_path, "rb") as image_file:
            # 读取图片为字节流
            image_bytes = image_file.read()
            # 编码为Base64字符串，并添加到列表中
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            base64_strings.append(base64_string)
    return base64_strings
# 把不同的地方绿色框标注起来
def mark_image_with_green_border(image_path, output_folder):
    """在图片周围画一个绿色的大框，并保存到指定的文件夹"""
    img = cv2.imread(image_path)
    height, width = img.shape[:2]
    cv2.rectangle(img, (0, 0), (width, height), (0, 255, 0), thickness=20)  # 使用绿色画一个大框
    output_path = os.path.join(output_folder, os.path.basename(image_path))
    cv2.imwrite(output_path, img)
# 找两张图片不同的地方
def find_and_mark_differences(image1_path, image2_path, output_folder):
    global similarity_list
    exists_difference = False  # 确保在引用之前已经定义并初始化
    # 读取两张图片
    img1 = cv2.imread(image1_path)
    img2 = cv2.imread(image2_path)

    # 将两张图片转换为灰度图
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 使用SSIM计算两张灰度图片的相似度
    ssim_index, _ = compare_ssim(gray1, gray2, full=True)

    # 从image1_path中提取页码
    page_number = int(os.path.basename(image1_path).split('_')[1].split('.')[0]) - 1  # 假设页码从1开始

    # 确保列表长度足够
    while len(similarity_list) <= page_number:
        similarity_list.append(None)

    # 存储相似度值
    similarity_list[page_number] = ssim_index

    print(f"Page {page_number + 1} SSIM (Similarity): {ssim_index}")

    # 计算差异并找到差异区域
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:  # 如果存在差异
        exists_difference = True

    # 将img2转换为BGR模式以便于在彩色模式下标注差异
    color_img2 = cv2.cvtColor(gray2, cv2.COLOR_GRAY2BGR)

    # 在color_img2上标注差异区域
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(color_img2, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # 构建输出路径并保存标注后的图片
    output_path = os.path.join(output_folder, os.path.basename(image2_path))
    cv2.imwrite(output_path, color_img2)

    return exists_difference
def adjust_sequences_based_on_similarity(mismatch_list, similarity_list, threshold=0.8):
    start_index = None  # 记录连续区间开始的索引
    continuous_sequences = []

    # 为了方便处理，将最后一个元素视作非连续，以触发最后一段连续区间的处理
    mismatch_list.append(float('inf'))

    for i in range(len(mismatch_list) - 1):
        # 检查当前页码与下一个页码是否连续
        if mismatch_list[i] + 1 == mismatch_list[i + 1]:
            if start_index is None:
                start_index = i
        else:
            # 当遇到非连续页码或者达到列表末尾时，检查之前的连续区间
            if start_index is not None and i - start_index >= 2:  # 确认连续区间长度超过3
                continuous_sequences.append((mismatch_list[start_index], mismatch_list[i]))
            start_index = None  # 重置连续区间的开始索引
    # 移除之前添加的哨兵元素
    mismatch_list.pop()

    adjusted_sequences = []

    for start, end in continuous_sequences:
        # 调整索引以符合Python的0基索引
        start_index = start - 1
        end_index = end - 1

        # 初始化当前序列的起始索引
        current_sequence_start = start_index
        for i in range(start_index, end_index + 1):
            # 如果当前值大于等于阈值
            if similarity_list[i] >= threshold:
                # 如果当前序列的起始索引小于i，说明找到了一个有效的序列
                if current_sequence_start < i:
                    adjusted_sequences.append((current_sequence_start + 1, i))
                # 更新当前序列的起始索引为下一个索引
                current_sequence_start = i + 1
        # 检查并添加最后一个序列
        if current_sequence_start <= end_index:
            adjusted_sequences.append((current_sequence_start + 1, end_index + 1))
        # 初始化一个新的mismatch_list
    # 初始化新的mismatch_list
    refined_mismatch_list = []

    # 创建一个集合，存储需要保留的页码
    pages_to_keep = set()

    # 添加adjusted_sequences中的起始页码
    for start, _ in adjusted_sequences:
        pages_to_keep.add(start)

    # 遍历mismatch_list，只保留不在adjusted_sequences指定范围内的页码
    for page in mismatch_list:
        # 检查当前页码是否在任一adjusted_sequences的范围内
        in_range = any(start <= page <= end for start, end in adjusted_sequences)
        # 如果不在范围内，或者是adjusted_sequences的起始页码，则保留
        if not in_range or page in pages_to_keep:
            refined_mismatch_list.append(page)

    return adjusted_sequences, refined_mismatch_list

# 主函数
def compare(pdf1_path, pdf2_path):
    pdf1_path = fitz.open(stream=BytesIO(pdf1_path))
    pdf2_path = fitz.open(stream=BytesIO(pdf2_path))
    # 转换PDF为图片并保存
    # pdf1_path = fitz.open(pdf1_path)
    # pdf2_path = fitz.open(pdf2_path)
    pdf_to_images(pdf1_path, PDF1_IMAGE)
    pdf_to_images(pdf2_path, PDF2_IMAGE)
    print("PDF转换并保存图片完成。")

    if not os.path.exists(RESULT_IMAGE):
        os.makedirs(RESULT_IMAGE)

    mismatch_list = []  # 用于记录不匹配的页号

    # 获取image1文件夹中的所有图片文件名
    images = [f for f in os.listdir(PDF1_IMAGE) if os.path.isfile(os.path.join(PDF1_IMAGE, f))]

    # 对每一对同名图片执行对比和标注操作
    for img_name in images:
        image1_path = os.path.join(PDF1_IMAGE, img_name)
        image2_path = os.path.join(PDF2_IMAGE, img_name)

        # 解析页号
        page_number = int(img_name.split('_')[1].split('.')[0])

        # 检查image2中是否存在对应的图片
        if os.path.exists(image2_path):
            if find_and_mark_differences(image1_path, image2_path, RESULT_IMAGE):
                mismatch_list.append(page_number)
        else:
            print(f"No corresponding image found for {img_name} in {PDF2_IMAGE}. Marking with green border.")
           # 假设页码从1开始
            # 确保列表长度足够
            while len(similarity_list) <= page_number:
                similarity_list.append(None)
            # 存储相似度值
            similarity_list[page_number-1] = 0
            mark_image_with_green_border(image1_path, RESULT_IMAGE)
            mismatch_list.append(page_number)


    print("Mismatched pages:", mismatch_list)
    print("Specified directories have been cleared.")
    # 对mismatch_list进行排序
    mismatch_list = sorted(mismatch_list)
    print(mismatch_list)


    print(len(similarity_list))
    adjusted_sequences, mismatch_list = adjust_sequences_based_on_similarity(mismatch_list, similarity_list)
    print(f"adjusted_sequences={adjusted_sequences}")
    print(f"mismathch_list={mismatch_list}")
    base64_strings = images_to_base64_list(RESULT_IMAGE, mismatch_list)
    print(len(mismatch_list))
    if not adjusted_sequences:
        return ""
    else:
        summaries = []
        for start, end in adjusted_sequences:
            summary = f"从{start}页开始到{end}页，两个文档格式相比变化很大。"
            summaries.append(summary)
        continuous = " ".join(summaries)
    print(continuous)
    dir_paths = [PDF1_IMAGE, PDF2_IMAGE,RESULT_IMAGE]
    clear_directory_contents(dir_paths)
    return mismatch_list, base64_strings, continuous


# 测试
# pdf1_path = 'pdf/1.pdf'  # 请根据实际情况修改路径
# pdf2_path = 'pdf/2.pdf'  # 请根据实际情况修改路径
# compare(pdf1_path, pdf2_path)

