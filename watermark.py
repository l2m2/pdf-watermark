"""
PDF 水印工具 - 压平式水印（难以用工具去除）

原理：将 PDF 每页渲染为高分辨率图片，在图片上叠加水印后重新合成 PDF。
水印成为像素数据的一部分，无法通过 PDF 编辑器的"删除图层/对象"操作去除。
"""

import os
import sys
import math
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
import img2pdf


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """尝试加载系统字体，回退到默认字体。"""
    font_candidates = [
        # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_watermark(
    img: Image.Image,
    text: str,
    opacity: int = 60,
    angle: int = 45,
    font_size_ratio: float = 0.06,
    color: tuple[int, int, int] = (180, 0, 0),
    repeat: bool = True,
    repeat_gap: int = 200,
) -> Image.Image:
    """
    在图片上绘制水印。

    Args:
        img:             原始 PIL 图片
        text:            水印文字
        opacity:         透明度 0-255（越高越不透明）
        angle:           旋转角度
        font_size_ratio: 字号占图片短边的比例
        color:           RGB 颜色
        repeat:          是否平铺重复水印
        repeat_gap:      平铺间距（像素）
    Returns:
        叠加水印后的 RGBA 图片
    """
    img = img.convert("RGBA")
    w, h = img.size

    font_size = max(20, int(min(w, h) * font_size_ratio))
    font = _get_font(font_size)

    # 在透明画布上画单个水印
    # 先测量文字尺寸
    tmp = Image.new("RGBA", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)
    bbox = tmp_draw.textbbox((0, 0), text, font=font)
    txt_w = bbox[2] - bbox[0] + 20
    txt_h = bbox[3] - bbox[1] + 20

    # 创建旋转后足够大的画布
    diag = int(math.hypot(txt_w, txt_h)) + 10
    stamp = Image.new("RGBA", (diag * 2, diag * 2), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp)
    cx, cy = diag, diag
    stamp_draw.text(
        (cx - txt_w // 2, cy - txt_h // 2),
        text,
        font=font,
        fill=(*color, opacity),
    )
    stamp = stamp.rotate(angle, expand=False)

    # 裁剪掉多余透明区域
    bbox2 = stamp.getbbox()
    if bbox2:
        stamp = stamp.crop(bbox2)

    sw, sh = stamp.size

    # 创建与原图等大的水印层
    watermark_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if repeat:
        # 平铺
        x = -sw
        while x < w + sw:
            y = -sh
            while y < h + sh:
                watermark_layer.paste(stamp, (x, y), stamp)
                y += sh + repeat_gap
            x += sw + repeat_gap
    else:
        # 居中单个
        watermark_layer.paste(stamp, ((w - sw) // 2, (h - sh) // 2), stamp)

    return Image.alpha_composite(img, watermark_layer)


def add_watermark(
    input_pdf: str,
    output_pdf: str,
    text: str,
    dpi: int = 200,
    opacity: int = 60,
    angle: int = 45,
    font_size_ratio: float = 0.06,
    color: tuple[int, int, int] = (180, 0, 0),
    repeat: bool = True,
    repeat_gap: int = 200,
) -> None:
    """
    给 PDF 添加压平式水印（水印不可分离）。

    Args:
        input_pdf:       输入 PDF 路径
        output_pdf:      输出 PDF 路径
        text:            水印文字
        dpi:             渲染分辨率（越高质量越好但文件越大，建议 150-300）
        opacity:         水印透明度 0-255
        angle:           水印旋转角度
        font_size_ratio: 字号占图片短边的比例
        color:           水印 RGB 颜色，默认红色
        repeat:          是否平铺
        repeat_gap:      平铺间距（像素）
    """
    input_pdf = str(Path(input_pdf).resolve())
    output_pdf = str(Path(output_pdf).resolve())

    print(f"正在将 PDF 渲染为图片（DPI={dpi}）...")
    pages = convert_from_path(input_pdf, dpi=dpi)
    print(f"共 {len(pages)} 页")

    with tempfile.TemporaryDirectory() as tmp_dir:
        image_paths = []
        for i, page in enumerate(pages, 1):
            print(f"  处理第 {i}/{len(pages)} 页...")
            watermarked = _draw_watermark(
                page,
                text=text,
                opacity=opacity,
                angle=angle,
                font_size_ratio=font_size_ratio,
                color=color,
                repeat=repeat,
                repeat_gap=repeat_gap,
            )
            # 转为 RGB（img2pdf 不接受 RGBA）
            rgb = Image.new("RGB", watermarked.size, (255, 255, 255))
            rgb.paste(watermarked, mask=watermarked.split()[3])

            out_path = os.path.join(tmp_dir, f"page_{i:04d}.jpg")
            rgb.save(out_path, "JPEG", quality=95)
            image_paths.append(out_path)

        print("正在合成 PDF...")
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(image_paths))

    print(f"完成！输出文件：{output_pdf}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def _parse_color(s: str) -> tuple[int, int, int]:
    parts = [int(x) for x in s.split(",")]
    if len(parts) != 3:
        raise ValueError("颜色格式应为 R,G,B，例如 180,0,0")
    return tuple(parts)  # type: ignore[return-value]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="给 PDF 添加压平式水印（水印融入图像，难以去除）"
    )
    parser.add_argument("input", help="输入 PDF 文件")
    parser.add_argument("output", help="输出 PDF 文件")
    parser.add_argument("--text", default="Gongwo Internal Doc", help="水印文字（默认：Gongwo Internal Doc）")
    parser.add_argument("--dpi", type=int, default=200, help="渲染分辨率（默认：200）")
    parser.add_argument("--opacity", type=int, default=60, help="透明度 0-255（默认：60）")
    parser.add_argument("--angle", type=int, default=45, help="旋转角度（默认：45）")
    parser.add_argument(
        "--font-size-ratio", type=float, default=0.06,
        help="字号占页面短边的比例（默认：0.06）"
    )
    parser.add_argument(
        "--color", default="180,0,0",
        help="水印 RGB 颜色，格式 R,G,B（默认：180,0,0 红色）"
    )
    parser.add_argument("--no-repeat", action="store_true", help="不平铺，仅居中单个水印")
    parser.add_argument("--repeat-gap", type=int, default=200, help="平铺间距像素（默认：200）")

    args = parser.parse_args()

    add_watermark(
        input_pdf=args.input,
        output_pdf=args.output,
        text=args.text,
        dpi=args.dpi,
        opacity=args.opacity,
        angle=args.angle,
        font_size_ratio=args.font_size_ratio,
        color=_parse_color(args.color),
        repeat=not args.no_repeat,
        repeat_gap=args.repeat_gap,
    )
