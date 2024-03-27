import base64
from io import BytesIO

import fitz
from PIL import Image


def pdf2img(page, dpi):
  img = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
  img_pil = Image.frombytes("RGB", [img.width, img.height], img.samples)
  grayscale_img = img_pil.convert('1')
  buffered = BytesIO()
  grayscale_img.save(buffered, format="PNG")
  img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
  return img_base64