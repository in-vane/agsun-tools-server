from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Tuple
from io import BytesIO
from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor
import fitz                 # PyMuPDF
from PIL import Image, ImageDraw

# ────────────── 常量 ──────────────
IMAGE_ROOT   = './file_system/images'
_OPACITY     = 0.3         # 高亮透明度
_Y_TOL       = 2.0         # 行归并 pt 容差
_Y_MATCH_TOL = 5.0         # 行匹配 y 容差
_MATCH_THR   = 0.75        # 行匹配阈值
CODE_SUCCESS = 0
CODE_ERROR = 1

# ────────────── 工具 ──────────────
def create_directory_path(type_id: str = '011') -> str:
    """创建并返回 /images/YYYY/MM/DD/type_id 目录（Linux 风格）"""
    now = datetime.now()
    path = os.path.join(
        IMAGE_ROOT,
        now.strftime('%Y'),
        now.strftime('%m'),
        now.strftime('%d'),
        type_id
    )
    os.makedirs(path, exist_ok=True)
    return os.path.normpath(path).replace('\\', '/')


def _norm_range(st: int, ed: int, total: int) -> Tuple[int, int]:
    if st == -1:
        st = 1
    if ed == -1:
        ed = total
    if st < 1 or ed < 1 or st > ed or ed > total:
        raise ValueError('页码非法')
    return st, ed


# ────────────── 文本提取 ──────────────
def _group_lines_by_y(spans: List[Dict], y_tol=_Y_TOL) -> List[Dict]:
    grouped: defaultdict[int, List[Dict]] = defaultdict(list)
    for s in spans:
        grouped[int(s['bbox'][1] / y_tol)].append(s)

    merged = []
    for y in sorted(grouped):
        row = sorted(grouped[y], key=lambda x: x['bbox'][0])
        text = ''.join(r['text'] for r in row)
        x0 = min(r['bbox'][0] for r in row)
        y0 = min(r['bbox'][1] for r in row)
        x1 = max(r['bbox'][2] for r in row)
        y1 = max(r['bbox'][3] for r in row)
        merged.append({'text': text, 'bbox': (x0, y0, x1, y1)})
    return merged


def extract_page_text(pdf_path: str, page_no: int) -> List[Dict]:
    """抽取指定页文字；页码超出范围返回 []"""
    with fitz.open(pdf_path) as doc:
        if not (1 <= page_no <= len(doc)):
            return []
        page = doc.load_page(page_no - 1)
        td = page.get_text('dict')

    spans = [
        {'text': span['text'], 'bbox': span['bbox']}
        for blk in td.get('blocks', [])
        for ln in blk.get('lines', [])
        for span in ln.get('spans', [])
        if span['text'].strip()
    ]
    spans.sort(key=lambda s: (int(s['bbox'][1]), int(s['bbox'][0])))
    return _group_lines_by_y(spans)


# ────────────── 行匹配 ──────────────
def _diff_two_lines(a: str, b: str) -> bool:
    """忽略空格后判断两行不同"""
    return ''.join(a.split()) != ''.join(b.split())


def _line_score(x: Dict, y: Dict) -> float:
    t1, t2 = x['text'].replace(' ', ''), y['text'].replace(' ', '')
    sim = SequenceMatcher(None, t1, t2, autojunk=False).ratio()
    dy = abs(x['bbox'][1] - y['bbox'][1])
    y_sc = max(0, 1 - dy / _Y_MATCH_TOL) if dy <= _Y_MATCH_TOL else 0
    len_sc = 1 - abs(len(t1)-len(t2)) / max(len(t1), len(t2)) if max(len(t1), len(t2)) else 0
    prefix = 0.2 if t1[:5] == t2[:5] else 0
    return 0.5*sim + 0.2*y_sc + 0.2*len_sc + 0.1*prefix


def _match_lines(a: List[Dict], b: List[Dict]):
    ua, ub = set(range(len(a))), set(range(len(b)))
    pairs = []

    def _try(rule):
        nonlocal ua, ub, pairs
        for i in list(ua):
            best, score = None, 0
            for j in list(ub):
                s = rule(a[i], b[j])
                if s > score:
                    best, score = j, s
            if score >= _MATCH_THR:
                pairs.append((i, best))
                ua.remove(i); ub.remove(best)

    rules = [
        lambda x, y: 1 if x['text'] == y['text'] else 0,
        lambda x, y: 0.95 if x['text'] == y['text'] and abs(x['bbox'][1]-y['bbox'][1])<=3 else 0,
        _line_score,
        lambda x, y: 0.85 if x['text'][:5]==y['text'][:5] and x['text'][-5:]==y['text'][-5:] else 0,
        lambda x, y: 0.8  if x['text'][:5]==y['text'][:5] else 0,
    ]
    for fn in rules:
        _try(fn)
    return pairs, ua, ub


def _compare_pages(n_lines, o_lines):
    diffs = []
    pairs, un_n, un_o = _match_lines(n_lines, o_lines)
    for i, j in pairs:
        if _diff_two_lines(n_lines[i]['text'], o_lines[j]['text']):
            diffs.append(('modify', n_lines[i]['bbox'], o_lines[j]['bbox']))
    for i in un_n:
        diffs.append(('insert', n_lines[i]['bbox'], None))
    for j in un_o:
        diffs.append(('delete', None, o_lines[j]['bbox']))
    return diffs


# ────────────── 图片渲染 ──────────────
def _page_to_image(pg: fitz.Page) -> Image.Image:
    pix = pg.get_pixmap()
    mode = 'RGB' if pix.alpha == 0 else 'RGBA'
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


def _draw_rect(im: Image.Image, bbox, color):
    if not bbox:
        return
    draw = ImageDraw.Draw(im, 'RGBA')
    x0, y0, x1, y1 = bbox
    draw.rectangle([x0, y0, x1, y1], fill=(*color, int(255*_OPACITY)))


def _save_pair_png(dn, do, np, op, diffs, type_id='011'):
    out_dir = create_directory_path(type_id)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    tag = f"{np or 0}_{op or 0}"

    # 原始图像
    img_n = _page_to_image(dn[np-1]) if np else Image.new('RGB', (1,1), 'white')
    img_o = _page_to_image(do[op-1]) if op else Image.new('RGB', (1,1), 'white')

    # 绘制高亮
    diff_n, diff_o = img_n.copy(), img_o.copy()
    for tp, b1, b2 in diffs:
        if tp in ('insert', 'modify') and b1:
            _draw_rect(diff_n, b1, (255,0,0))
        if tp in ('delete', 'modify') and b2:
            _draw_rect(diff_o, b2, (0,0,255))

    # 拼接
    w, h = img_n.width+img_o.width, max(img_n.height, img_o.height)
    combo_diff = Image.new('RGB', (w,h), 'white')
    combo_orig = Image.new('RGB', (w,h), 'white')
    combo_diff.paste(diff_n, (0,0)); combo_diff.paste(diff_o, (img_n.width,0))
    combo_orig.paste(img_n, (0,0)); combo_orig.paste(img_o, (img_n.width,0))

    diff_path = os.path.join(out_dir, f"{timestamp}_{tag}_diff.png")
    orig_path = os.path.join(out_dir, f"{timestamp}_{tag}_orig.png")
    combo_diff.save(diff_path); combo_orig.save(orig_path)

    # 返回 Linux 风格路径
    return (os.path.normpath(diff_path).replace('\\','/'),
            os.path.normpath(orig_path).replace('\\','/'))


# ────────────── 主入口 ──────────────

def check_pdf_text(
    username:str,
    file1: str, file2: str,
    start_1: int, end_1: int,
    start_2: int, end_2: int,
    type_id: str = '011'
):
    """
    对比指定页区间
    返回:
        (code, diff_pages, image_paths, error_msg, extra_msg)

        code        : CODE_SUCCESS / CODE_ERROR
        diff_pages  : [15, 15, 17, 17, ...]   # 一维，若失败为空
        image_paths : ['...diff.png', '...orig.png', ...]
        error_msg   : '没有差异' 或 '[15, 17]页有差异' 或 校验/系统错误信息
        extra_msg   : 预留字段（暂返回 ''）
    """
    try:
        dn, do = fitz.open(file1), fitz.open(file2)
    except Exception as e:                 # 打开 PDF 失败
        return CODE_ERROR, [], [], '', f'打开文件失败: {e}'

    # ── 校验页码区间 ──────────────────────────
    try:
        s1, e1 = _norm_range(start_1, end_1, len(dn))
        s2, e2 = _norm_range(start_2, end_2, len(do))
    except ValueError as ve:               # _norm_range 已覆盖非法输入
        dn.close(); do.close()
        return CODE_ERROR, [], [], str(ve), ''

    # 两区间长度必须一致
    if (e1 - s1) != (e2 - s2):
        dn.close(); do.close()
        return CODE_ERROR, [], [], '输入页号错误：两区间页数不一致', ''

    # ── 开始逐页对比 ──────────────────────────
    list_n = list(range(s1, e1 + 1))
    list_o = list(range(s2, e2 + 1))
    diff_pages, image_paths, pages_set = [], [], set()

    for np, op in zip(list_n, list_o):     # 长度已相等，可直接 zip
        nl = extract_page_text(file1, np)
        ol = extract_page_text(file2, op)
        diffs = _compare_pages(nl, ol)

        if diffs:
            diff_pages.extend([np, op])
            pages_set.update([np, op])
            p_diff, p_orig = _save_pair_png(dn, do, np, op, diffs, type_id)
            image_paths.extend([p_diff, p_orig])

    dn.close(); do.close()

    if not diff_pages:
        return CODE_SUCCESS, [], [], '没有差异', ''

    error_msg = f"[{', '.join(map(str, sorted(pages_set)))}]页有差异"
    return CODE_SUCCESS, diff_pages, image_paths, error_msg, ''



class PdfTextHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file1, file2, start_1, end_1, start_2, end_2, mode):
        return check_pdf_text(username, file1, file2, start_1, end_1, start_2, end_2, mode)
    async def post(self):
        username = self.current_user
        param = tornado.escape.json_decode(self.request.body)
        print(f"传入参数为:{param}")
        file_path_1 = param['file_path_1']
        file_path_2 = param['file_path_2']
        start_1 = int(param.get('start_1', -1))
        end_1 = int(param.get('end_1', -1))
        start_2 = int(param.get('start_2', -1))
        end_2 = int(param.get('end_2', -1))
        mode = int(param.get('mode', 0))
        code, pages, image_paths, error_msg, msg = await self.process_async(username,
                                                                file_path_1, file_path_2, start_1, end_1, start_2, end_2, mode)
        custom_data = {
            "code": code,
            "data": {
                'pages': pages,
                'image_paths': image_paths,
                'error_msg': error_msg
            },
            "msg": msg
        }

        self.write(custom_data)
