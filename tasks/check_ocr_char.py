import base64
import difflib
from io import BytesIO

import cv2
import fitz
import easyocr
import numpy as np
from PIL import Image


DPI = 300
BASE64_JPG = 'data:image/jpeg;base64,'


class ocrImg2imgDifference(object):
    def __init__(self, img1, img2, lang):
        self.img1 = img1
        self.img2 = img2
        self.lang = lang
        self.reader = easyocr.Reader(self.lang)

    # 两个检测框框是否有交叉，如果有交集则返回重叠度 IOU, 如果没有交集则返回 0
    def bb_overlab(self, x1, y1, w1, h1, x2, y2, w2, h2):
        '''
        说明：图像中，从左往右是 x 轴（0~无穷大），从上往下是 y 轴（0~无穷大），从左往右是宽度 w ，从上往下是高度 h
        :param x1: 第一个框的左上角 x 坐标
        :param y1: 第一个框的左上角 y 坐标
        :param w1: 第一幅图中的检测框的宽度
        :param h1: 第一幅图中的检测框的高度
        :param x2: 第二个框的左上角 x 坐标
        :param y2:
        :param w2:
        :param h2:
        :return: 两个如果有交集则返回重叠度 IOU, 如果没有交集则返回 0
        '''
        if (x1 > x2 + w2):
            return 0
        if (y1 > y2 + h2):
            return 0
        if (x1 + w1 < x2):
            return 0
        if (y1 + h1 < y2):
            return 0
        colInt = abs(min(x1 + w1, x2 + w2) - max(x1, x2))
        rowInt = abs(min(y1 + h1, y2 + h2) - max(y1, y2))
        overlap_area = colInt * rowInt
        area1 = w1 * h1
        area2 = w2 * h2
        return overlap_area / (area1 + area2 - overlap_area)

    # 对齐两个image
    def imgRefine(self, img1, img2):
        # 对齐两幅图像，同时将图像缩放到同一比例
        shape0 = int(img2.shape[0])
        shape1 = int(img2.shape[1])
        img1 = cv2.resize(img1, dsize=(shape1, shape0))
        sift = cv2.SIFT_create()

        # 检测关键点
        kp1, des1 = sift.detectAndCompute(img1, None)
        kp2, des2 = sift.detectAndCompute(img2, None)

        # 关键点匹配
        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=6)
        search_params = dict(checks=10)

        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)
        
        # 把good中的左右点分别提出来找单应性变换
        pts_src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        pts_dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask = cv2.findHomography(pts_src, pts_dst, cv2.RANSAC, 5.0)

        result = cv2.warpPerspective(img1, M, (img1.shape[1], img1.shape[0]))

        before_gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
        after_gray = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)

        return before_gray, after_gray

    def findGoodMatch(self, result1, result2):
        # 找到两个图像中文字的最佳匹配，基于IOU量度
        # to fill
        len1 = len(result1)
        len2 = len(result2)
        match = np.zeros(len1)
        for i in range(len1):
            x1 = result1[i][0][0][0]
            y1 = result1[i][0][0][1]
            w1 = result1[i][0][1][0] - result1[i][0][0][0]
            h1 = result1[i][0][2][1] - result1[i][0][0][1]
            matchValue = 0
            for j in range(len2):
                x2 = result2[j][0][0][0]
                y2 = result2[j][0][0][1]
                w2 = result2[j][0][1][0] - result2[j][0][0][0]
                h2 = result2[j][0][2][1] - result2[j][0][0][1]

                temp = self.bb_overlab(x1, y1, w1, h1, x2, y2, w2, h2)
                if (temp >= matchValue):
                    match[i] = j
                    matchValue = temp
        unMatch = np.zeros(len2)
        for i in range(len1):
            unMatch[int(match[i])] = 1

        return match, unMatch

    # 给出text的位置，标记相应的错误处
    def markDifference(self, result1, result2, before_img1, after_img2, match, unMatch):
        d = difflib.Differ()
        for i in range(len(result1)):
            diff = d.compare(result1[i][1], result2[int(match[i])][1])
            compareList = list(diff)
            len1 = len(result1[i][1])
            len2 = len(result2[int(match[i])][1])
            count1 = 0
            count2 = 0
            countJ1 = 0
            countJ2 = 0
            x1_1 = 0
            y1_1 = 0
            x1_2 = 0
            y1_2 = 0
            h1_1 = 0
            h1_2 = 0
            radius = 0

            for j in range(len(compareList)):
                if compareList[j][0] == '-':
                    if count1 == 1:
                        countJ1 = j - count2
                    w1 = result1[i][0][1][0] - result1[i][0][0][0]
                    h1 = int(result1[i][0][2][1] - result1[i][0][0][1])
                    x1 = int(result1[i][0][0][0])  # + (count1) * int(w1 / len1))
                    y1 = int(result1[i][0][0][1])
                    radius = int(w1 / len1)
                    x1_1 = x1
                    y1_1 = y1
                    h1_1 = h1
                    count1 = count1 + 1
                if compareList[j][0] == '+':
                    if count2 == 1:
                        countJ2 = j - count1
                    w1 = result2[int(match[i])][0][1][0] - result2[int(match[i])][0][0][0]
                    h1 = int(result2[int(match[i])][0][2][1] - result2[int(match[i])][0][0][1])
                    x1 = int(result2[int(match[i])][0][0][0])  # + (count2) * int(w1 / len2))
                    y1 = int(result2[int(match[i])][0][0][1])
                    radius = int(w1 / len2)
                    x1_2 = x1
                    y1_2 = y1
                    h1_2 = h1
                    count2 = count2 + 1
            if count1 != 0:
                w1 = count1 * radius
                x1 = x1_1 + countJ1 * radius
                y1 = y1_1
                h1 = h1_1
                after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0
                after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0
            if count2 != 0:
                w1 = count2 * radius
                x1 = x1_2 + countJ2 * radius
                y1 = y1_2
                h1 = h1_2
                after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0
                after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0
        for i in range(unMatch.shape[0]):
            if unMatch[i] == 0:
                w1 = int(result2[i][0][1][0] - result2[i][0][0][0])
                h1 = int(result2[i][0][2][1] - result2[i][0][0][1])
                x1 = int(result2[i][0][0][0])
                y1 = int(result2[i][0][0][1])
                after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0
                after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0

        return before_img1, after_img2

        # 给出text的位置，标记相应的错误处

    def markDifferenceRate(self, result1, result2, before_img1, after_img2, match, unMatch, rate):
        d = difflib.Differ()
        gray = np.abs(before_img1 - after_img2)
        gray = cv2.medianBlur(gray, ksize=5)

        dstDiffHarr = cv2.cornerHarris(gray, 2, 3, 0.04)
        flagImg = np.zeros(dstDiffHarr.shape)
        flagImg[dstDiffHarr > rate * dstDiffHarr.max()] = 1

        for i in range(len(result1)):
            diff = d.compare(result1[i][1], result2[int(match[i])][1])
            compareList = list(diff)
            len1 = len(result1[i][1])
            len2 = len(result2[int(match[i])][1])
            count1 = 0
            count2 = 0
            countJ1 = 0
            countJ2 = 0
            x1_1 = 0
            y1_1 = 0
            x1_2 = 0
            y1_2 = 0
            h1_1 = 0
            h1_2 = 0
            radius = 0
            for j in range(len(compareList)):
                if compareList[j][0] == '-':
                    if count1 == 1:
                        countJ1 = j - count2
                    w1 = result1[i][0][1][0] - result1[i][0][0][0]
                    h1 = int(result1[i][0][2][1] - result1[i][0][0][1])
                    x1 = int(result1[i][0][0][0])  # + (count1) * int(w1 / len1))
                    # x1 = int(result1[i][0][0][0] )
                    y1 = int(result1[i][0][0][1])
                    radius = int(w1 / len1)
                    x1_1 = x1
                    y1_1 = y1
                    h1_1 = h1
                    count1 = count1 + 1
                if compareList[j][0] == '+':
                    if count2 == 1:
                        countJ2 = j - count1
                    w1 = result2[int(match[i])][0][1][0] - result2[int(match[i])][0][0][0]
                    h1 = int(result2[int(match[i])][0][2][1] - result2[int(match[i])][0][0][1])
                    x1 = int(result2[int(match[i])][0][0][0])  # + (count2) * int(w1 / len2))
                    y1 = int(result2[int(match[i])][0][0][1])
                    radius = int(w1 / len2)
                    x1_2 = x1
                    y1_2 = y1
                    h1_2 = h1
                    count2 = count2 + 1
            if count1 != 0:
                w1 = count1 * radius
                x1 = x1_1 + countJ1 * radius
                y1 = y1_1
                h1 = h1_1
                new_img = flagImg[y1:(y1 + h1), x1:(x1 + w1)]
                sum = new_img.sum()
                if (sum > 0):
                    after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                    after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0

                    after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                    after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0
            if count2 != 0:
                w1 = count2 * radius
                x1 = x1_2 + countJ2 * radius
                y1 = y1_2
                h1 = h1_2
                new_img = flagImg[y1:(y1 + h1), x1:(x1 + w1)]
                sum = new_img.sum()
                if (sum > 0):
                    after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                    after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0

                    after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                    after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0
        for i in range(unMatch.shape[0]):
            if unMatch[i] == 0:
                w1 = int(result2[i][0][1][0] - result2[i][0][0][0])
                h1 = int(result2[i][0][2][1] - result2[i][0][0][1])
                x1 = int(result2[i][0][0][0])
                y1 = int(result2[i][0][0][1])
                # before_img1[y1:(y1 + 10), x1:(x1 + 10)] = 255
                after_img2[y1:(y1 + 3), x1:(x1 + w1)] = 0
                after_img2[(y1 + h1):(y1 + h1 + 3), x1:(x1 + w1)] = 0

                after_img2[y1:(y1 + h1), x1:(x1 + 3)] = 0
                after_img2[(y1):(y1 + h1), (x1 + w1):(x1 + w1 + 3)] = 0

        return before_img1, after_img2

    def returnMarkImage(self):
        img1 = self.img1  # cv2.imread(self.path1)
        img2 = self.img2  # cv2.imread(self.path2)

        before_img1, after_img2 = self.imgRefine(img1, img2)
        result1 = self.reader.readtext(before_img1)
        result2 = self.reader.readtext(after_img2)
        self.result = result2
        # print(result1)
        match, unMatch = self.findGoodMatch(result1, result2)
        before_img1, after_img2 = self.markDifference(result1, result2, before_img1, after_img2, match, unMatch)
        return before_img1, after_img2

    def returnPdfText(self):
        return self.result


class ocrImg2ImgDifference(ocrImg2imgDifference):
    def __init__(self, lang):
        self.reader = easyocr.Reader(lang)

    def returnMarkImageImg2img(self, img1, img2):
        before_img1, after_img2 = self.imgRefine(img1, img2)
        result1 = self.reader.readtext(before_img1)
        result2 = self.reader.readtext(after_img2)
        self.result = result2
        # print(result1)
        match, unMatch = self.findGoodMatch(result1, result2)
        before_img1, after_img2 = self.markDifference(result1, result2, before_img1, after_img2, match, unMatch)
        return before_img1, after_img2


def check_ocr_char(img_base64, pdf):
    # 解码 base64 字符串为图像数据
    image_data_1 = base64.b64decode(img_base64)
    nparr_1 = np.frombuffer(image_data_1, np.uint8)
    img1 = cv2.imdecode(nparr_1, cv2.IMREAD_COLOR)
    
    doc = fitz.open(stream=BytesIO(pdf))
    page = doc.load_page(0)
    image = page.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
    img_array = np.frombuffer(image.samples, dtype=np.uint8).reshape((image.height, image.width, 3))
    doc.close()
    img2 = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    diff = ocrImg2ImgDifference(['en', 'hu'])
    before_img1, after_img2 = diff.returnMarkImageImg2img(img1, img2)

    _, image_buffer = cv2.imencode('.jpeg', before_img1)
    image_base64_1 = base64.b64encode(image_buffer).decode('utf-8')
    _, image_buffer = cv2.imencode('.jpeg', after_img2)
    image_base64_2 = base64.b64encode(image_buffer).decode('utf-8')
    
    error = True

    return error, f"{BASE64_JPG}{image_base64_1}", f"{BASE64_JPG}{image_base64_2}"