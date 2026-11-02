import os
import math
from PIL import Image, ImageDraw

# Brand constants from frontend/src/index.css
GREEN_BG = (61, 99, 77)       # #3D634D
WHITE = (255, 255, 255)       # #FFFFFF
WHITE_A15 = (255, 255, 255, 38)

PUBLIC_DIR = os.path.abspath("frontend/public")
os.makedirs(PUBLIC_DIR, exist_ok=True)

SVG_CONTENT = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <!-- Simplistic Green Rounded Square -->
  <rect width="512" height="512" rx="112" fill="#3D634D" />
  
  <!-- Minimalist Compass Icon (Lucide Geometry Scaled) -->
  <g transform="translate(106, 106) scale(12.5)" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
  </g>
</svg>
'''

def render_logo_image(size: int) -> Image.Image:
    """
    Renders the green square + compass logo with 4x supersampling for flawless anti-aliasing.
    """
    supersample = 4
    canvas_size = size * supersample
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Draw rounded square
    corner_radius = int(canvas_size * (112 / 512))
    draw.rounded_rectangle(
        [0, 0, canvas_size - 1, canvas_size - 1],
        radius=corner_radius,
        fill=GREEN_BG,
    )

    # 2. Draw Compass
    # Geometry scaled to canvas
    center = canvas_size / 2.0
    scale = (canvas_size * (300 / 512)) / 24.0  # Lucide 24x24 scale
    stroke_w = max(2, int(2.0 * scale))

    # Outer Circle: r = 10 in 24x24
    circle_r = 10.0 * scale
    draw.ellipse(
        [
            center - circle_r,
            center - circle_r,
            center + circle_r,
            center + circle_r,
        ],
        outline=WHITE,
        width=stroke_w,
    )

    # Needle Polygon: (16.24, 7.76), (14.12, 14.12), (7.76, 16.24), (9.88, 9.88)
    # in 24x24 coords, origin at center - 12 * scale
    origin_x = center - 12.0 * scale
    origin_y = center - 12.0 * scale

    poly_pts_24 = [
        (16.24, 7.76),
        (14.12, 14.12),
        (7.76, 16.24),
        (9.88, 9.88),
    ]
    poly_pts = [
        (origin_x + px * scale, origin_y + py * scale)
        for px, py in poly_pts_24
    ]

    # Draw needle lines with round joints
    for i in range(len(poly_pts)):
        p1 = poly_pts[i]
        p2 = poly_pts[(i + 1) % len(poly_pts)]
        draw.line([p1, p2], fill=WHITE, width=stroke_w, joint="curve")

    # Downsample using Lanczos
    rescaled = img.resize((size, size), Image.Resampling.LANCZOS)
    return rescaled


def main():
    print(f"Generating branding assets in {PUBLIC_DIR}...")

    # 1. Save SVG files
    favicon_svg_path = os.path.join(PUBLIC_DIR, "favicon.svg")
    with open(favicon_svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT.strip())
    print(f"  Saved: {favicon_svg_path}")

    logo_svg_path = os.path.join(PUBLIC_DIR, "logo.svg")
    with open(logo_svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT.strip())
    print(f"  Saved: {logo_svg_path}")

    # 2. Render PNGs
    sizes = [
        ("logo.png", 1024),         # Ultra high-res marketing / Google
        ("icon-512.png", 512),       # PWA large icon
        ("icon-192.png", 192),       # PWA standard icon
        ("favicon-32x32.png", 32),   # Standard tab favicon
    ]

    for fname, sz in sizes:
        out_path = os.path.join(PUBLIC_DIR, fname)
        img = render_logo_image(sz)
        img.save(out_path, format="PNG", optimize=True)
        print(f"  Saved: {out_path} ({sz}x{sz}px)")

    # 3. Create Multi-Resolution favicon.ico
    ico_path = os.path.join(PUBLIC_DIR, "favicon.ico")
    img_16 = render_logo_image(16)
    img_32 = render_logo_image(32)
    img_48 = render_logo_image(48)
    img_48.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[img_32, img_16],
    )
    print(f"  Saved: {ico_path} (multi-res ICO)")

    print("Brand assets successfully generated!")

if __name__ == "__main__":
    main()

