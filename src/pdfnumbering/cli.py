"""
Command line interface to the package.
"""

import argparse
import shutil
import sys
import tempfile

import pypdf

from pdfnumbering import __version__
from pdfnumbering.color import hex2rgb
from pdfnumbering.core import Align, PdfNumberer


def create_parser():
    """
    Create parser for CLI arguments.
    """
    parser = argparse.ArgumentParser(
        description="Stamp pages in a PDF document with page numbers.",
        allow_abbrev=False,
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    numbering = parser.add_argument_group("numbering options")
    numbering.add_argument(
        "--first-number",
        metavar="N",
        default=1,
        type=int,
        help="number to start counting from (default: %(default)s)",
    )
    numbering.add_argument(
        "--ignore-pages",
        metavar="PAGE",
        nargs="*",
        default=(),
        type=int,
        help="pages that should not be counted",
    )
    numbering.add_argument(
        "--skip-pages",
        metavar="PAGE",
        nargs="*",
        default=(),
        type=int,
        help="pages that should not be stamped",
    )
    numbering.add_argument(
        "--stamp-format",
        metavar="STRING",
        default="{}",
        help='format string for stamp text, formatted with page number and page count (default: "{}")',
    )

    styling = parser.add_argument_group("styling options")
    styling.add_argument(
        "--font-size",
        metavar="PT",
        default=12,
        type=int,
        help="font size in points (default: %(default)s)",
    )
    styling.add_argument(
        "--font-family",
        metavar="NAME",
        default="Helvetica",
        help="font family name (default: %(default)s)",
    )
    styling.add_argument(
        "--text-color",
        metavar="HEX",
        default="#000000",
        help="hexadecimal color code (default: %(default)s)",
    )

    placement = parser.add_argument_group("placement options")
    placement.add_argument(
        "--text-align",
        default="center",
        choices=("left", "center", "right"),
        help="horizontal alignment of page numbers (default: %(default)s)",
    )
    placement.add_argument(
        "--text-position",
        metavar=("X", "Y"),
        nargs=2,
        default=(-1, -1),
        type=int,
        help="position of page numbers, in points (default: 0 0)",
    )
    placement.add_argument(
        "--position",
        default="",
        choices=("bc", "bl", "br", "tr", "tc", "tl"),
        type=str,
        help="position of page numbers, in points (default: 0 0)",
    )
    placement.add_argument(
        "--page-margin",
        metavar=("X", "Y"),
        nargs=2,
        type=int,
        help="margin at the page edges, in points (default: adapts to font size)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="",
        help="destination to write output to",
    )
    parser.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("rb"),
        help="the input PDF file to stamp",
    )

    return parser


def process_args(args) -> tuple[argparse.Namespace, str | None]:
    """
    Post-process parsed CLI arguments.
    """
    # Refuse to write binary data to terminal
    if not args.output and sys.stdout.isatty():
        return args, "--output must be specified or stdout redirected."

    # Parse hex color code to RGB tuple
    try:
        args.text_color = hex2rgb(args.text_color)
    except ValueError as error:
        return args, f"argument --text-color: {error}"

    # Convert align string choice to enum value
    args.text_align = Align.coerce(args.text_align[0].upper())

    # Adapt vertical margins to font size by default
    if args.page_margin is None:
        args.page_margin = (10, 10 + args.font_size // 2)

    # Convert pages from 1-based to 0-based indexing
    args.ignore_pages = [page - 1 for page in args.ignore_pages]
    args.skip_pages = [page - 1 for page in args.skip_pages]

    # If position is specified it shall take priority over the (x, y)
    # positioning and text alignment
    if args.position == "bc":
        args.text_position = (0, -1)
        args.text_align = Align.C
    elif args.position == "br":
        args.text_position = (-1, -1)
        args.text_align = Align.R
    elif args.position == "bl":
        args.text_position = (0, -1)
        args.text_align = Align.L
    elif args.position == "tc":
        args.text_position = (0.49, 0.99)
    elif args.position == "tr":
        args.text_position = (0.99, 0.99)
        args.text_align = Align.R
    elif args.position == "tl":
        args.text_position = (0, 0.99)
        args.text_align = Align.L
    else:
        # Default to bottom center
        args.text_position = (0, -1)
        args.text_align = Align.C

    return args, None


def main():
    """
    Command line entrypoint.
    """
    parser = create_parser()
    args = parser.parse_args()
    args, error = process_args(args)
    if error is not None:
        parser.error(error)

    numberer = PdfNumberer(
        first_number=args.first_number,
        ignore_pages=args.ignore_pages,
        skip_pages=args.skip_pages,
        stamp_format=args.stamp_format,
        font_size=args.font_size,
        font_family=args.font_family,
        text_color=args.text_color,
        text_align=args.text_align,
        text_position=args.text_position,
        page_margin=args.page_margin,
    )

    document = pypdf.PdfWriter(clone_from=args.file)
    numberer.add_page_numbering(document.pages)
    # support paginating in-place
    if not args.output:
        args.output = sys.stdout.buffer
    elif args.output == args.file.name:
        with tempfile.NamedTemporaryFile("wb") as tmp:
            print(f"{tmp.name}")
            document.write(tmp)
            shutil.copyfile(tmp.name, args.output)
    else:
        with open(args.output, "wb") as out:
            document.write(out)

        document.write(args.output or sys.stdout.buffer)


if __name__ == "__main__":
    main()
