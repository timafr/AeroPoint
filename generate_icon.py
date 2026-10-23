import os
import json
import math
from PIL import Image, ImageDraw, ImageFilter

def create_app_icon():
    size = 1024
    img = Image.new("RGBA", (size, size), (7, 5, 13, 255))
    draw = ImageDraw.Draw(img)

    # 1. Radial background ambient glow
    for r in range(500, 50, -10):
        alpha = int(35 * (1.0 - r / 500.0))
        draw.ellipse(
            [(size//2 - r, size//2 - r), (size//2 + r, size//2 + r)],
            fill=(138, 43, 226, alpha)
        )

    # 2. LiDAR dToF concentric scanning circles
    for r in [180, 280, 380, 460]:
        draw.ellipse(
            [(size//2 - r, size//2 - r), (size//2 + r, size//2 + r)],
            outline=(0, 242, 254, 40),
            width=2
        )

    # 3. Holographic Hand joints & bones
    # Scaled 21-joint coordinates centered in 1024x1024
    cx, cy = 512, 540
    scale = 320.0

    raw_joints = [
        # 0: Wrist
        (0.0, 0.42),
        # 1-4: Thumb
        (-0.16, 0.28), (-0.26, 0.14), (-0.32, -0.02), (-0.36, -0.16),
        # 5-8: Index
        (-0.12, 0.02), (-0.14, -0.16), (-0.15, -0.30), (-0.16, -0.44),
        # 9-12: Middle
        (0.02, -0.01), (0.02, -0.20), (0.02, -0.36), (0.02, -0.52),
        # 13-16: Ring
        (0.15, 0.04), (0.17, -0.14), (0.18, -0.28), (0.19, -0.42),
        # 17-20: Pinky
        (0.26, 0.12), (0.29, -0.04), (0.31, -0.16), (0.33, -0.28)
    ]

    pts = []
    for rx, ry in raw_joints:
        px = int(cx + rx * scale)
        py = int(cy + ry * scale)
        pts.append((px, py))

    connections = [
        (0,1), (1,2), (2,3), (3,4),
        (0,5), (5,6), (6,7), (7,8),
        (5,9), (9,10), (10,11), (11,12),
        (9,13), (13,14), (14,15), (15,16),
        (13,17), (17,18), (18,19), (19,20),
        (0,17)
    ]

    # Draw neon glow bones
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    for p1, p2 in connections:
        glow_draw.line([pts[p1], pts[p2]], fill=(138, 43, 226, 180), width=16)
        glow_draw.line([pts[p1], pts[p2]], fill=(0, 242, 254, 255), width=6)

    # Blur glow layer
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=6))
    img.alpha_composite(glow_layer)

    # Re-draw crisp center bone lines
    top_draw = ImageDraw.Draw(img)
    for p1, p2 in connections:
        top_draw.line([pts[p1], pts[p2]], fill=(255, 255, 255, 230), width=3)

    # Draw Joints
    tips = [4, 8, 12, 16, 20]
    for idx, (px, py) in enumerate(pts):
        is_tip = idx in tips
        is_wrist = idx == 0

        if is_tip:
            # Magenta glowing tip
            rad = 18
            top_draw.ellipse([(px - rad, py - rad), (px + rad, py + rad)], fill=(255, 0, 128, 255))
            top_draw.ellipse([(px - rad + 4, py - rad + 4), (px + rad - 4, py + rad - 4)], fill=(255, 255, 255, 255))
            # Cyan ring around tip
            top_draw.ellipse([(px - rad - 6, py - rad - 6), (px + rad + 6, py + rad + 6)], outline=(0, 242, 254, 200), width=3)
        elif is_wrist:
            rad = 16
            top_draw.ellipse([(px - rad, py - rad), (px + rad, py + rad)], fill=(0, 242, 254, 255))
            top_draw.ellipse([(px - rad + 4, py - rad + 4), (px + rad - 4, py + rad - 4)], fill=(255, 255, 255, 255))
        else:
            rad = 10
            top_draw.ellipse([(px - rad, py - rad), (px + rad, py + rad)], fill=(138, 43, 226, 255))
            top_draw.ellipse([(px - rad + 3, py - rad + 3), (px + rad - 3, py + rad - 3)], fill=(255, 255, 255, 255))

    # Spatial beam target pulse at index tip
    itx, ity = pts[8]
    for r in [32, 52, 74]:
        top_draw.ellipse([(itx - r, ity - r), (itx + r, ity + r)], outline=(0, 242, 254, 140), width=2)

    # Save asset catalog
    dest_dir = r"c:\hands\ios\AeroPointSpatial\Sources\AeroPointSpatial\Assets.xcassets\AppIcon.appiconset"
    os.makedirs(dest_dir, exist_ok=True)

    master_path = os.path.join(dest_dir, "AppIcon-1024.png")
    # Convert RGBA to RGB (Apple App Store & Xcode require no alpha channel on 1024x1024 icon)
    final_icon = Image.new("RGB", (size, size), (7, 5, 13))
    final_icon.paste(img, (0, 0), img)
    final_icon.save(master_path, "PNG")
    print(f"[+] Master 1024x1024 icon saved to {master_path}")

    # Generate standard iPhone sizes
    sizes = {
        "AppIcon-180.png": 180,
        "AppIcon-120.png": 120,
        "AppIcon-87.png": 87,
        "AppIcon-80.png": 80,
        "AppIcon-58.png": 58
    }

    for fname, sz in sizes.items():
        sub_img = final_icon.resize((sz, sz), Image.Resampling.LANCZOS)
        sub_path = os.path.join(dest_dir, fname)
        sub_img.save(sub_path, "PNG")

    contents = {
        "images": [
            {
                "idiom": "universal",
                "platform": "ios",
                "size": "1024x1024",
                "filename": "AppIcon-1024.png"
            },
            {
                "idiom": "iphone",
                "size": "60x60",
                "scale": "3x",
                "filename": "AppIcon-180.png"
            },
            {
                "idiom": "iphone",
                "size": "60x60",
                "scale": "2x",
                "filename": "AppIcon-120.png"
            },
            {
                "idiom": "iphone",
                "size": "40x40",
                "scale": "3x",
                "filename": "AppIcon-120.png"
            },
            {
                "idiom": "iphone",
                "size": "40x40",
                "scale": "2x",
                "filename": "AppIcon-80.png"
            },
            {
                "idiom": "iphone",
                "size": "29x29",
                "scale": "3x",
                "filename": "AppIcon-87.png"
            },
            {
                "idiom": "iphone",
                "size": "29x29",
                "scale": "2x",
                "filename": "AppIcon-58.png"
            }
        ],
        "info": {
            "author": "xcode",
            "version": 1
        }
    }

    contents_path = os.path.join(dest_dir, "Contents.json")
    with open(contents_path, "w", encoding="utf-8") as f:
        json.dump(contents, f, indent=2)

    print(f"[+] Contents.json created at {contents_path}")

if __name__ == "__main__":
    create_app_icon()
