"""Generiert docs/banner.svg im Ember-Look des Dashboards.

Links Typo (Micro-Label, Titel, Subline), rechts ein Activity-Ring mit Flamme
über einem dezenten Heatmap-Punktfeld. Deterministisch (fester Seed).
"""
import math
import os
import random

W, H = 1200, 300
random.seed(11)

# Heatmap-Punktfeld: 7 Zeilen x 16 Spalten, rechts, hinter dem Ring.
dots = []
cell, gap = 13, 7
grid_w = 16 * (cell + gap) - gap
x0 = 760
y0 = (H - (7 * (cell + gap) - gap)) / 2
for col in range(16):
    for row in range(7):
        x = x0 + col * (cell + gap)
        y = y0 + row * (cell + gap)
        trained = random.random() < 0.62
        if trained:
            o = round(random.uniform(0.10, 0.30), 2)
            fill = "#d8a657"
        else:
            o = 0.05
            fill = "#ffffff"
        dots.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="3.5" '
            f'fill="{fill}" opacity="{o}"/>'
        )
dots_svg = "\n    ".join(dots)

# Activity-Ring: 2/3 gefüllt, Start oben (rotate -90 um Zentrum).
CX, CY, R = 985, 150, 74
CIRC = 2 * math.pi * R
OFFSET = CIRC * (1 - 4 / 6)

# Flamme aus dem Dashboard (viewBox 0 0 32 40), aufs Ringzentrum skaliert.
FLAME_SCALE = 1.85
fx = CX - 16 * FLAME_SCALE
fy = CY - 20 * FLAME_SCALE

svg = f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="round"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26"/></clipPath>
    <radialGradient id="glow-warm" cx="0.82" cy="0.1" r="0.75">
      <stop offset="0%" stop-color="#d8a657" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#d8a657" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow-cool" cx="0.05" cy="1.05" r="0.7">
      <stop offset="0%" stop-color="#577cd8" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#577cd8" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="ember-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#d8a657"/><stop offset="100%" stop-color="#f0c078"/>
    </linearGradient>
    <radialGradient id="ring-halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#d8a657" stop-opacity="0.22"/>
      <stop offset="70%" stop-color="#d8a657" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="#d8a657" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <g clip-path="url(#round)">
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="#0c0d10"/>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="url(#glow-warm)"/>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="url(#glow-cool)"/>

    <!-- Heatmap-Punktfeld -->
    {dots_svg}

    <!-- Activity-Ring mit Flamme -->
    <circle cx="{CX}" cy="{CY}" r="{R + 46}" fill="url(#ring-halo)"/>
    <circle cx="{CX}" cy="{CY}" r="{R + 22}" fill="#0c0d10" opacity="0.82"/>
    <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="12"/>
    <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="url(#ember-grad)" stroke-width="12"
      stroke-linecap="round" stroke-dasharray="{CIRC:.1f}" stroke-dashoffset="{OFFSET:.1f}"
      transform="rotate(-90 {CX} {CY})"/>
    <g transform="translate({fx:.1f} {fy:.1f}) scale({FLAME_SCALE})">
      <path fill="#d8a657" d="M16 39c8 0 12-5.5 12-12.5 0-6-3-9.5-4.8-13.7-1-2.3-1.4-4.7-1-8.3-4 2-7 6.7-6.4 11.3-2.3-1.6-3.6-4.3-3.6-7.6-3.6 3.3-6.2 8.6-6.2 13.8C6 33.5 8 39 16 39z"/>
      <path fill="#f0c078" d="M16.5 36.5c5.4 0 8-3.7 8-8.3 0-4-2-6.6-3.4-9.3-.5 2-1.7 3.6-3.3 4.6.4-3.3-1-6.2-3.3-8-.4 2.6-1.7 4.7-3.6 6.2-1.6 1.3-2.7 3.5-2.7 6C8 33 11 36.5 16.5 36.5z"/>
      <path fill="#f8e3bb" d="M17 34.5c2.8 0 4.3-2.1 4.3-4.7 0-2-1.3-3.5-2.2-4.8-.4 1.4-1.2 2.4-2.3 3-.2-1.8-1.1-3.2-2.3-4-.1 1.6-.8 2.9-1.8 3.8-.8.7-1.3 1.9-1.3 3.1 0 2.6 1.8 3.6 5.6 3.6z"/>
    </g>

    <!-- Typo links -->
    <text x="72" y="112" font-family="-apple-system, 'Segoe UI', system-ui, sans-serif"
      font-size="15" font-weight="600" letter-spacing="5" fill="#6d6f6a">PERSONAL FITNESS TRACKING</text>
    <text x="72" y="172" font-family="-apple-system, 'Segoe UI', system-ui, sans-serif"
      font-size="54" font-weight="300" letter-spacing="-1" fill="#f3f4f1">Trainings-Tracker</text>
    <text x="72" y="214" font-family="-apple-system, 'Segoe UI', system-ui, sans-serif"
      font-size="19" font-weight="400" fill="#a5a7a1">Loggen per Telegram in freier Sprache&#160;&#160;·&#160;&#160;PWA-Dashboard&#160;&#160;·&#160;&#160;läuft komplett kostenlos</text>

    <rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="25.5" fill="none" stroke="rgba(255,255,255,0.10)" stroke-width="1"/>
  </g>
</svg>
"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner.svg")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(svg)
print("geschrieben:", out)
