"""生成测试 PDF 并加水印，验证功能正常。"""

import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


def create_test_pdf(path: str) -> None:
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    for i in range(1, 4):
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(w / 2, h / 2 + 20, f"Test Page {i}")
        c.setFont("Helvetica", 18)
        c.drawCentredString(w / 2, h / 2 - 30, "This is confidential content.")
        if i < 3:
            c.showPage()
    c.save()
    print(f"测试 PDF 已生成：{path}")


if __name__ == "__main__":
    # 生成测试 PDF
    test_input = "test_input.pdf"
    test_output = "test_output_watermarked.pdf"
    create_test_pdf(test_input)

    # 加水印
    from watermark import add_watermark
    add_watermark(
        input_pdf=test_input,
        output_pdf=test_output,
        text="机密文件  CONFIDENTIAL",
        dpi=150,
        opacity=70,
        angle=35,
    )

    size = os.path.getsize(test_output)
    print(f"输出文件大小：{size / 1024:.1f} KB")
    print("测试完成！")
