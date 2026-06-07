"""
Generate FileDiff.app icon — 1024x1024 PNG
macOS Big Sur / Sonoma aesthetic: deep navy-to-indigo gradient, two floating
document cards with diff lines (red/green highlights), subtle shadows.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math, os

FONT_DIR = (
    "/Users/sittichaitaykum/Library/Application Support/Claude/"
    "local-agent-mode-sessions/skills-plugin/93ec793a-737d-4fa2-aaca-dda1d5b3db51/"
    "61c9dc03-9c15-4c68-853e-3e03cc9cf4ea/skills/canvas-design/canvas-fonts"
)

SIZE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon_1024.png")

# ── Colours ────────────────────────────────────────────────────────────────
BG_TOP    = (15,  23,  58)   # deep navy
BG_BOT    = (30,  58, 110)   # indigo-blue
CARD_L    = (235, 243, 255)  # ice-blue tint
CARD_R    = (240, 248, 240)  # ice-green tint
LINE_NORM = (190, 200, 215)  # normal text line
LINE_ADD  = ( 52, 199, 107)  # green  – added
LINE_DEL  = (255,  69,  82)  # red    – deleted
LINE_MOD  = (255, 159,  10)  # amber  – modified
ARROW     = (255, 255, 255)
LABEL_FG  = (180, 200, 240)

# ── Canvas ──────────────────────────────────────────────────────────────────
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 1. macOS rounded-rect background ─────────────────────────────────────────
RADIUS = 224
bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
bg_draw = ImageDraw.Draw(bg)

# Gradient fill via scanlines
for y in range(SIZE):
    t = y / SIZE
    r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
    g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
    b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
    bg_draw.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

# Clip to rounded rect mask
mask = Image.new("L", (SIZE, SIZE), 0)
mask_draw = ImageDraw.Draw(mask)
mask_draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=RADIUS, fill=255)
img.paste(bg, (0, 0), mask)
draw = ImageDraw.Draw(img)

# 2. Subtle inner glow ring ─────────────────────────────────────────────────
glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for i in range(18, 0, -1):
    alpha = int(30 * (i / 18))
    gd.rounded_rectangle(
        [i * 2, i * 2, SIZE - i * 2 - 1, SIZE - i * 2 - 1],
        radius=RADIUS - i * 2,
        outline=(100, 160, 255, alpha),
        width=2,
    )
img = Image.alpha_composite(img, glow)
draw = ImageDraw.Draw(img)

# 3. Two floating document cards ────────────────────────────────────────────
GAP      = 40          # gap between cards
CARD_W   = 340
CARD_H   = 450
CARD_Y   = (SIZE - CARD_H) // 2 - 10
CX       = SIZE // 2
CARD_L_X = CX - GAP // 2 - CARD_W      # left card left edge
CARD_R_X = CX + GAP // 2               # right card left edge
CARD_RAD = 22

def draw_card(x, y, w, h, fill, shadow_alpha=80):
    # Drop shadow
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i in range(20, 0, -1):
        a = int(shadow_alpha * (i / 20) ** 2)
        sd.rounded_rectangle(
            [x + i, y + i, x + w + i, y + h + i],
            radius=CARD_RAD + 2, fill=(0, 0, 0, a)
        )
    return shadow

shadow_l = draw_card(CARD_L_X, CARD_Y, CARD_W, CARD_H, CARD_L)
shadow_r = draw_card(CARD_R_X, CARD_Y, CARD_W, CARD_H, CARD_R)
img = Image.alpha_composite(img, shadow_l)
img = Image.alpha_composite(img, shadow_r)
draw = ImageDraw.Draw(img)

# Card faces
draw.rounded_rectangle(
    [CARD_L_X, CARD_Y, CARD_L_X + CARD_W, CARD_Y + CARD_H],
    radius=CARD_RAD, fill=(*CARD_L, 255)
)
draw.rounded_rectangle(
    [CARD_R_X, CARD_Y, CARD_R_X + CARD_W, CARD_Y + CARD_H],
    radius=CARD_RAD, fill=(*CARD_R, 255)
)

# Card top colour strips (like a file-type accent)
STRIP_H = 52
draw.rounded_rectangle(
    [CARD_L_X, CARD_Y, CARD_L_X + CARD_W, CARD_Y + STRIP_H],
    radius=CARD_RAD, fill=(70, 130, 220, 255)
)
draw.rectangle(
    [CARD_L_X, CARD_Y + STRIP_H // 2, CARD_L_X + CARD_W, CARD_Y + STRIP_H],
    fill=(70, 130, 220, 255)
)
draw.rounded_rectangle(
    [CARD_R_X, CARD_Y, CARD_R_X + CARD_W, CARD_Y + STRIP_H],
    radius=CARD_RAD, fill=(52, 180, 100, 255)
)
draw.rectangle(
    [CARD_R_X, CARD_Y + STRIP_H // 2, CARD_R_X + CARD_W, CARD_Y + STRIP_H],
    fill=(52, 180, 100, 255)
)

# 4. Text lines with diff highlights ──────────────────────────────────────
# (line_left_color, line_right_color)
LINES = [
    (LINE_NORM,  LINE_NORM),   # equal
    (LINE_NORM,  LINE_NORM),
    (LINE_DEL,   LINE_ADD),    # replace
    (LINE_NORM,  LINE_NORM),
    (LINE_MOD,   LINE_MOD),    # modified
    (LINE_NORM,  LINE_NORM),
    (LINE_NORM,  LINE_ADD),    # insert on right
    (LINE_NORM,  LINE_NORM),
    (LINE_DEL,   LINE_NORM),   # delete on left
    (LINE_NORM,  LINE_NORM),
    (LINE_NORM,  LINE_NORM),
    (LINE_NORM,  LINE_NORM),
]

# Widths that simulate varying line lengths (L, R)
WIDTHS_L = [0.82, 0.60, 0.75, 0.88, 0.55, 0.78, 0.90, 0.50, 0.70, 0.84, 0.62, 0.74]
WIDTHS_R = [0.82, 0.60, 0.68, 0.88, 0.55, 0.78, 0.90, 0.50, 0.80, 0.84, 0.62, 0.74]

LINE_H    = 28
LINE_LH   = 10   # left padding inside card
LINE_TH   = 8    # line bar thickness
LINES_START_Y = CARD_Y + STRIP_H + 28
MAX_LINE_W = CARD_W - LINE_LH * 2

for i, ((lc, rc), wl, wr) in enumerate(zip(LINES, WIDTHS_L, WIDTHS_R)):
    ly = LINES_START_Y + i * LINE_H

    # Highlight band for diff lines
    if lc != LINE_NORM:
        hl = (*lc, 35)
        draw.rectangle(
            [CARD_L_X + 6, ly - 2, CARD_L_X + CARD_W - 6, ly + LINE_TH + 4],
            fill=hl
        )
    if rc != LINE_NORM:
        hr = (*rc, 35)
        draw.rectangle(
            [CARD_R_X + 6, ly - 2, CARD_R_X + CARD_W - 6, ly + LINE_TH + 4],
            fill=hr
        )

    # Left card lines
    bar_w_l = int(MAX_LINE_W * wl)
    draw.rounded_rectangle(
        [CARD_L_X + LINE_LH, ly,
         CARD_L_X + LINE_LH + bar_w_l, ly + LINE_TH],
        radius=4, fill=(*lc, 210)
    )

    # Right card lines
    bar_w_r = int(MAX_LINE_W * wr)
    draw.rounded_rectangle(
        [CARD_R_X + LINE_LH, ly,
         CARD_R_X + LINE_LH + bar_w_r, ly + LINE_TH],
        radius=4, fill=(*rc, 210)
    )

# 5. Centre diff arrows ────────────────────────────────────────────────────
# Two small arrow chevrons ◀ ▶ in the gap
AY = SIZE // 2
AX = SIZE // 2

# Left arrow ◀
pts_l = [
    (AX - 14, AY),
    (AX - 4,  AY - 10),
    (AX - 4,  AY + 10),
]
draw.polygon(pts_l, fill=(*ARROW, 200))

# Right arrow ▶
pts_r = [
    (AX + 14, AY),
    (AX + 4,  AY - 10),
    (AX + 4,  AY + 10),
]
draw.polygon(pts_r, fill=(*ARROW, 200))

# Small circle behind arrows
draw.ellipse(
    [AX - 26, AY - 26, AX + 26, AY + 26],
    fill=(255, 255, 255, 22)
)

# 6. "FileDiff" label at bottom ────────────────────────────────────────────
try:
    font_path = os.path.join(FONT_DIR, "GeistMono-Bold.ttf")
    font_label = ImageFont.truetype(font_path, 52)
except Exception:
    font_label = ImageFont.load_default()

label = "FileDiff"
bbox = draw.textbbox((0, 0), label, font=font_label)
lw = bbox[2] - bbox[0]
lx = (SIZE - lw) // 2
ly_label = CARD_Y + CARD_H + 40
draw.text((lx, ly_label), label, font=font_label, fill=(*LABEL_FG, 220))

# 7. Subtle specular highlight on background ───────────────────────────────
spec = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
spec_draw = ImageDraw.Draw(spec)
spec_draw.ellipse([100, 60, 700, 420], fill=(255, 255, 255, 14))
spec = spec.filter(ImageFilter.GaussianBlur(80))
img = Image.alpha_composite(img, spec)

# 8. Save ─────────────────────────────────────────────────────────────────
img.save(OUT)
print(f"Saved: {OUT}  ({SIZE}×{SIZE})")
