"""Utility for rendering images as ANSI colored half-block art in the terminal.

Example (CLI):
    python show_image.py image1.png -w 120 -a 2.05

Embedding in code:
    from show_image import TerminalImageRenderer
    renderer = TerminalImageRenderer(char_aspect=2.0)
    art = renderer.render_to_string('image1.png', width=120)
    print(art)
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional

from PIL import Image

RESET = "\x1b[0m"


def _supports_truecolor() -> bool:
    """Very naive truecolor capability check; can be expanded later."""
    # Common env hints
    if os.environ.get("COLORTERM", "").lower() in {"truecolor", "24bit"}:
        return True
    # Assume modern terminals (Windows Terminal, VS Code, etc.) support it
    return True


@dataclass
class RenderOptions:
    width: int = 100
    char_aspect: float = 2.0  # terminal cell height / width
    scale: float = 1.0        # additional uniform width scale
    truecolor: Optional[bool] = None  # autodetect if None


class TerminalImageRenderer:
    """Render images to ANSI colored half-block strings.

    Uses the upper half block (\u2580) combining a foreground color (top pixel)
    and background color (bottom pixel) for double vertical resolution.
    """

    def __init__(self, options: Optional[RenderOptions] = None, **kwargs):
        if options is None:
            # Allow passing width, char_aspect, etc. directly
            options = RenderOptions(**kwargs)
        self.options = options
        if self.options.truecolor is None:
            self.options.truecolor = _supports_truecolor()

    def _ansi(self, r: int, g: int, b: int, *, bg: bool = False) -> str:
        if not self.options.truecolor:
            # Fallback: map to 216-color cube (simplistic) if needed
            # r,g,b 0..255 -> 0..5
            rc = int(r / 51)
            gc = int(g / 51)
            bc = int(b / 51)
            color_index = 16 + 36 * rc + 6 * gc + bc
            return f"\x1b[{48 if bg else 38};5;{color_index}m"
        return f"\x1b[{48 if bg else 38};2;{r};{g};{b}m"

    def _compute_target_size(self, img: Image.Image, width: int, char_aspect: float) -> tuple[int, int]:
        w, h = img.size
        aspect = h / w  # image aspect (height/width)
        target_w = width
        target_h = int(2 * aspect * target_w / char_aspect)
        if target_h % 2:
            target_h += 1
        return target_w, max(2, target_h)

    def render_to_string(self, path: str, width: Optional[int] = None, char_aspect: Optional[float] = None) -> str:
        opts = self.options
        width = int((width if width is not None else opts.width) * opts.scale)
        char_aspect = char_aspect if char_aspect is not None else opts.char_aspect
        img = Image.open(path).convert("RGB")
        target_w, target_h = self._compute_target_size(img, width, char_aspect)
        if img.size != (target_w, target_h):
            img = img.resize((target_w, target_h))
        pixels = img.load()
        lines: list[str] = []
        for y in range(0, target_h, 2):
            row_parts: list[str] = []
            for x in range(target_w):
                top = pixels[x, y]
                bottom = pixels[x, y + 1] if y + 1 < target_h else top
                row_parts.append(f"{self._ansi(*top)}{self._ansi(*bottom, bg=True)}▀")
            lines.append("".join(row_parts) + RESET)
        return "\n".join(lines)

    def print(self, path: str, **kwargs) -> None:  # convenience
        print(self.render_to_string(path, **kwargs))


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render an image as ANSI colored half-blocks.")
    p.add_argument("image", nargs="?", default="image1.png", help="Image file path")
    p.add_argument("-w", "--width", type=int, default=100, help="Target character width")
    p.add_argument("-a", "--char-aspect", type=float, default=float(os.environ.get("CHAR_CELL_ASPECT", "2.0")), help="Terminal character cell aspect ratio (height/width). Typical values: 1.9-2.2")
    p.add_argument("-s", "--scale", type=float, default=1.0, help="Additional uniform scale multiplier applied after width")
    p.add_argument("--no-truecolor", action="store_true", help="Force 256-color mode instead of truecolor")
    return p


def displayImage(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    renderer = TerminalImageRenderer(
        width=int(args.width),
        char_aspect=args.char_aspect,
        scale=args.scale,
        truecolor=not args.no_truecolor,
    )
    try:
        renderer.print(args.image)
    except FileNotFoundError:
        print(f"Error: file not found: {args.image}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # CLI entry
    raise SystemExit(displayImage())
