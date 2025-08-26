"""Utility for rendering images as ANSI colored half-block art in the terminal.

Example (CLI):
    python show_image.py image1.png -w 120 -a 2.05

Embedding in code:
    from show_image import TerminalImageRenderer
    renderer = TerminalImageRenderer(char_aspect=2.0)
    art = renderer.render_to_string('image1.png', width=120)
    print(art)

Note for Windows users:
    If you see ��� characters in the output, run 'chcp 65001' in your console
    to enable UTF-8 encoding before running this script.
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


def _enable_windows_console_utf8_and_ansi() -> None:
    """Best-effort: enable UTF-8 and ANSI escapes on Windows consoles.

    - Sets console output code page to 65001 (UTF-8)
    - Enables Virtual Terminal Processing so ANSI sequences render
    """
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # Set UTF-8 code page
        kernel32.SetConsoleOutputCP(65001)

        # Enable Virtual Terminal Processing
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        ENABLE_PROCESSED_OUTPUT = 0x0001

        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING | ENABLE_PROCESSED_OUTPUT
            kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        # Best-effort only; ignore if this environment doesn't support it
        pass


@dataclass
class RenderOptions:
    width: int = 100
    char_aspect: float = 2.0  # terminal cell height / width
    scale: float = 1.0        # additional uniform width scale
    truecolor: Optional[bool] = None  # autodetect if None
    ascii: bool = False       # force ASCII block replacement
    char: str = "▀"            # default glyph (U+2580 upper half block)


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
        # Ensure RGB values are valid (0-255)
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        # Avoid problematic color combinations that may cause encoding issues
        # Some specific RGB combinations seem to create invalid sequences
        if (r, g, b) in [(255, 255, 255), (0, 0, 0)]:
            # Use slightly different values for pure white/black to avoid edge cases
            if r == 255 and g == 255 and b == 255:
                r, g, b = 254, 254, 254
            elif r == 0 and g == 0 and b == 0:
                r, g, b = 1, 1, 1

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
                try:
                    top = pixels[x, y]
                    bottom = pixels[x, y + 1] if y + 1 < target_h else top
                    # Ensure RGB values are tuples/valid
                    if not isinstance(top, (tuple, list)) or len(top) < 3:
                        top = (0, 0, 0)
                    if not isinstance(bottom, (tuple, list)) or len(bottom) < 3:
                        bottom = (0, 0, 0)

                    # Choose glyph with fallback
                    if opts.ascii:
                        char = "#"
                    else:
                        # Prefer configured glyph; validate against console encoding
                        candidate = opts.char or "▀"
                        try:
                            (candidate or "").encode(sys.stdout.encoding or "utf-8")
                            char = candidate
                        except (UnicodeEncodeError, AttributeError):
                            char = "#"  # ASCII fallback

                    # Build the colored character string with error handling
                    # Combine FG and BG into a single SGR to avoid mid-escape glitches
                    tr, tg, tb = int(top[0]), int(top[1]), int(top[2])
                    br, bg, bb = int(bottom[0]), int(bottom[1]), int(bottom[2])
                    colored_char = f"\x1b[38;2;{tr};{tg};{tb};48;2;{br};{bg};{bb}m{char}"

                    # Test if the sequence can be encoded properly
                    try:
                        colored_char.encode(sys.stdout.encoding or 'utf-8')
                        row_parts.append(colored_char)
                    except (UnicodeEncodeError, UnicodeError):
                        # Fallback to safe character if encoding fails
                        safe_char = "#"
                        try:
                            safe_char.encode(sys.stdout.encoding or 'utf-8')
                            row_parts.append(safe_char)
                        except (UnicodeEncodeError, UnicodeError):
                            # Ultimate fallback - just use # without colors
                            row_parts.append("#")

                except (IndexError, TypeError, ValueError, UnicodeError):
                    # Fallback for any pixel access or encoding issues
                    row_parts.append(f"{self._ansi(0, 0, 0)}{self._ansi(0, 0, 0, bg=True)}#")
            eol = "\r\n" if os.name == "nt" else "\n"
            lines.append("".join(row_parts) + RESET + eol)

        # Compose final result (avoid global encode-replace which can inject U+FFFD)
        return "".join(lines)

    def print(self, path: str, **kwargs) -> None:  # convenience
        try:
            output = self.render_to_string(path, **kwargs)
            # Write bytes directly to avoid partial-encoding artifacts
            data = output.encode("utf-8", errors="strict")
            sys.stdout.buffer.write(data)
            if not output.endswith("\n"):
                sys.stdout.buffer.write(b"\n")
            sys.stdout.flush()
        except UnicodeEncodeError:
            # Re-render in ASCII mode to guarantee compatibility
            alt_opts = RenderOptions(**self.options.__dict__)
            alt_opts.ascii = True
            alt_renderer = TerminalImageRenderer(options=alt_opts)
            fallback = alt_renderer.render_to_string(
                path,
                width=kwargs.get("width"),
                char_aspect=kwargs.get("char_aspect"),
            )
            sys.stdout.write(fallback + ("" if fallback.endswith("\n") else "\n"))
            sys.stdout.flush()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render an image as ANSI colored half-blocks.")
    p.add_argument("image", nargs="?", default="image1.png", help="Image file path")
    p.add_argument("-w", "--width", type=int, default=100, help="Target character width")
    p.add_argument("-a", "--char-aspect", type=float, default=float(os.environ.get("CHAR_CELL_ASPECT", "2.0")), help="Terminal character cell aspect ratio (height/width). Typical values: 1.9-2.2")
    p.add_argument("-s", "--scale", type=float, default=1.0, help="Additional uniform scale multiplier applied after width")
    p.add_argument("--no-truecolor", action="store_true", help="Force 256-color mode instead of truecolor")
    p.add_argument("--ascii", action="store_true", help="Force ASCII fallback for block glyphs (#)")
    return p


def displayImage(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    _enable_windows_console_utf8_and_ansi()
    renderer = TerminalImageRenderer(
        width=int(args.width),
        char_aspect=args.char_aspect,
        scale=args.scale,
        truecolor=not args.no_truecolor,
        ascii=bool(args.ascii),
    )
    try:
        renderer.print(args.image)
    except FileNotFoundError:
        print(f"Error: file not found: {args.image}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # CLI entry
    raise SystemExit(displayImage())
