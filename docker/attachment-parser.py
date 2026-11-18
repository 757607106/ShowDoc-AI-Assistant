"""Fixed chat attachment parser, executed only inside the parser sandbox image."""
import json
import sys
from pathlib import Path


def parse(path):
    if path.suffix.lower() in {'.txt', '.md', '.csv', '.tsv', '.json', '.xml', '.html', '.htm', '.yaml', '.yml', '.log', '.py', '.js', '.ts', '.sql', '.css'}:
        return path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.docx':
        from docx import Document
        document = Document(path)
        return '\n'.join([p.text for p in document.paragraphs] + ['\t'.join(cell.text for cell in row.cells) for table in document.tables for row in table.rows])
    if path.suffix.lower() in {'.xlsx', '.xlsm'}:
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            return '\n\n'.join('# ' + sheet.title + '\n' + '\n'.join('\t'.join('' if v is None else str(v) for v in row) for row in sheet.iter_rows(values_only=True)) for sheet in book)
        finally:
            book.close()
    if path.suffix.lower() == '.pptx':
        from pptx import Presentation
        return '\n\n'.join('\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame) for slide in Presentation(path).slides)
    if path.suffix.lower() == '.pdf':
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(path)
        try:
            pages = []
            for index in range(len(document)):
                page = document[index]
                text = page.get_textpage()
                try:
                    pages.append(text.get_text_range())
                finally:
                    text.close()
                    page.close()
            result = '\n\n'.join(pages)
            if result.strip():
                return result
        finally:
            document.close()
    from docling.document_converter import DocumentConverter
    return DocumentConverter().convert(path).document.export_to_markdown()


def model_image(path, limit, formats):
    from io import BytesIO
    from PIL import Image
    with Image.open(path) as image:
        mime = Image.MIME.get(image.format)
        if mime not in {'image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/bmp', 'image/tiff'}:
            raise ValueError('Unsupported model image')
        if (not formats or mime in formats) and (not limit or path.stat().st_size <= limit):
            image.verify()
            return {'mime': mime}
        pixels = image.convert('RGBA')
    target = next((fmt for fmt in ('image/jpeg', 'image/png') if not formats or fmt in formats), None)
    if not target:
        raise ValueError('No supported output format')
    if target == 'image/jpeg':
        background = Image.new('RGB', pixels.size, 'white')
        background.paste(pixels, mask=pixels.getchannel('A'))
        pixels = background
    while True:
        output = BytesIO()
        pixels.save(output, 'JPEG' if target == 'image/jpeg' else 'PNG', quality=85)
        if not limit or output.tell() <= limit:
            path.with_name('model-image').write_bytes(output.getvalue())
            return {'mime': target, 'converted': True}
        size = tuple(int(side * 0.75) for side in pixels.size)
        if min(size) < 64:
            raise ValueError('Image exceeds the model size limit')
        pixels = pixels.resize(size, Image.Resampling.BILINEAR)


if __name__ == '__main__':
    if sys.argv[2:3] == ['--model-image']:
        print(json.dumps(model_image(Path(sys.argv[1]), int(sys.argv[3]), sys.argv[4:])))
    elif sys.argv[2:] == ['--image']:
        from PIL import Image
        with Image.open(sys.argv[1]) as image:
            mime = Image.MIME.get(image.format)
            image.verify()
        if mime not in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}:
            raise ValueError('Unsupported image')
        print(json.dumps({'mime': mime}))
    else:
        text = parse(Path(sys.argv[1]))
        if not text.strip() or len(text) > 4_000_000:
            raise ValueError('Attachment text is empty or exceeds the limit')
        print(json.dumps({'text': text}, ensure_ascii=False))
