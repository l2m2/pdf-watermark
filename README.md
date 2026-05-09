# pdf-watermark

给 PDF 添加**压平式水印**——水印直接融入页面像素，无法通过 PDF 编辑器删除图层或对象的方式去除。

## 原理

普通 PDF 水印以独立对象/图层存在，可被 Adobe Acrobat、在线工具等轻松删除。本工具采用压平（flatten）方案：

1. 用 poppler 将每页渲染为高分辨率位图
2. 用 Pillow 将水印直接绘制进像素数据
3. 用 img2pdf 将图片重新合成 PDF

水印成为图像像素的一部分，不存在可独立删除的 PDF 对象。

## 依赖

**Python 包**

```bash
pip install -r requirements.txt
```

**系统依赖（poppler）**

```bash
# macOS
brew install poppler

# Ubuntu / Debian
sudo apt install poppler-utils

# CentOS / RHEL
sudo yum install poppler-utils
```

## 用法

### 命令行

```bash
python watermark.py <input.pdf> <output.pdf> [选项]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--text` | `机密文件` | 水印文字 |
| `--dpi` | `200` | 渲染分辨率，越高质量越好文件越大 |
| `--opacity` | `60` | 透明度 0–255 |
| `--angle` | `45` | 旋转角度 |
| `--font-size-ratio` | `0.06` | 字号占页面短边的比例 |
| `--color` | `180,0,0` | 水印颜色，格式 `R,G,B` |
| `--no-repeat` | — | 不平铺，仅居中显示单个水印 |
| `--repeat-gap` | `200` | 平铺间距（像素） |

**示例**

```bash
# 默认红色斜向平铺水印
python watermark.py contract.pdf contract_wm.pdf --text "机密文件"

# 自定义颜色、透明度、角度
python watermark.py report.pdf report_wm.pdf \
  --text "CONFIDENTIAL" \
  --dpi 300 \
  --opacity 80 \
  --angle 30 \
  --color 0,0,180
```

### Python API

```python
from watermark import add_watermark

add_watermark(
    input_pdf="input.pdf",
    output_pdf="output.pdf",
    text="机密文件",
    dpi=200,
    opacity=60,
    angle=45,
    color=(180, 0, 0),
)
```

## 注意事项

- 压平后 PDF 为纯图像，文字不可选中/复制，文件体积会增大
- `dpi=150` 适合一般用途，`dpi=300` 适合需要打印的场景
- 中文水印需要系统中存在支持中文的字体（macOS 默认已有）
