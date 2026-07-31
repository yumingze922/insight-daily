"""
生成 PWA 图标（使用 PIL/Pillow）

运行：python scripts/generate_icons.py
"""

import os
from pathlib import Path

def generate_icons():
    """生成简单的 PWA 图标（纯色背景 + 文字）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("需要安装 Pillow：pip install Pillow")
        print("或者手动将图标放到 public/icons/ 目录")
        return

    icons_dir = Path(__file__).parent.parent / "public" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    sizes = [72, 96, 128, 144, 152, 192, 512]
    bg_color = (28, 25, 21)      # 墨黑色
    text_color = (212, 192, 140)  # 金色

    for size in sizes:
        img = Image.new('RGB', (size, size), bg_color)
        draw = ImageDraw.Draw(img)

        # 尝试加载中文字体
        font_size = int(size * 0.42)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # 绘制"思"字居中
        bbox = draw.textbbox((0, 0), "思", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2 - int(size * 0.02)
        draw.text((x, y), "思", fill=text_color, font=font)

        filepath = icons_dir / f"icon-{size}.png"
        img.save(filepath, "PNG")
        print(f"  ✅ icon-{size}.png")

    print(f"\n所有图标已生成到：{icons_dir}")

if __name__ == "__main__":
    generate_icons()
