import io
import math
from dataclasses import dataclass
from typing import Container, Iterable

import fpdf
import pypdf
from fpdf import Align

from .color import hex2rgb

Page = pypdf.PageObject


@dataclass(slots=True, kw_only=True)
class PdfNumberer:
    color: str = "#ff0000"
    font_size: int = 32
    font_family: str = "Helvetica"
    align: str | Align = Align.L
    position: tuple[int, int] = (0, 0)
    margin: tuple[int, int] = (28, 28)
    start: int = 1
    ignore: Container[int] = ()
    skip: Container[int] = ()

    def add_page_numbering(self, pages: Iterable[Page]) -> None:
        """
        Stamp PDF pages with page numbers.
        """
        page_numbers = self._create_page_numbers(pages)
        for page_number, page in zip(page_numbers, pages):
            if page_number is not None:
                page.merge_page(self._create_stamp(page, str(page_number)))

    def _create_page_numbers(self, pages: Iterable[Page]) -> Iterable[int | None]:
        page_number = self.start
        for page in pages:
            if page.page_number in self.ignore:
                yield None
            elif page.page_number in self.skip:
                yield None
                page_number += 1
            else:
                yield page_number
                page_number += 1

    def _create_stamp(self, page: Page, text: str) -> Page:
        pdf = fpdf.FPDF(unit="pt")
        pdf.set_auto_page_break(False)  # Allow small negative y-positions
        pdf.set_font(self.font_family, size=self.font_size)
        pdf.set_text_color(*hex2rgb(self.color))

        pdf.add_page(format=(page.mediabox.width, page.mediabox.height))
        pdf.set_y(math.copysign(self.margin[1], self.position[1]) + self.position[1])
        pdf.set_x(math.copysign(self.margin[0], self.position[0]) + self.position[0])
        pdf.cell(0, 0, text, align=self.align)

        def to_pypdf(pdf: fpdf.FPDF) -> pypdf.PdfReader:
            return pypdf.PdfReader(io.BytesIO(pdf.output()))

        return to_pypdf(pdf).pages[0]
