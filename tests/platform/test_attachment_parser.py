import json
import io
import os
from unittest.mock import Mock

import pytest
from opensandbox.models.execd import Execution, ExecutionError, ExecutionLogs, OutputMessage

from governance.store import StoreError
from webapi.chat_resources import _image_mime, _parse_attachment


def test_parser_uses_official_sandbox_files_and_argv_with_no_credentials_or_host_mounts(monkeypatch):
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=0, logs=ExecutionLogs(
        stdout=[OutputMessage(text=json.dumps({'text': '隔离正文\n'}), timestamp=0)]))
    create = Mock(return_value=native)
    monkeypatch.setattr('opensandbox.SandboxSync.create', create)
    connection = object()
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: connection)
    assert _parse_attachment('evil; command.txt', b'input') == '隔离正文\n'
    options = create.call_args.kwargs
    assert create.call_args.args == ('showdoc-attachment-parser:local',)
    assert options['connection_config'] is connection
    assert options['env'] == {} and options['volumes'] == []
    assert options['network_policy'].default_action == 'deny'
    written = native.files.write_files.call_args.args[0]
    assert len(written) == 1 and written[0].path == '/tmp/input.txt'
    assert written[0].data == b'input' and written[0].mode == 644
    command = native.commands.run.call_args
    assert command.args[0] == ['python', '/opt/attachment-parser.py', '/tmp/input.txt']
    assert command.kwargs['opts'].uid is None and command.kwargs['opts'].timeout.total_seconds() == 180
    native.destroy.assert_called_once()


def test_model_image_preparation_converts_transparent_input_and_respects_size(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    from PIL import Image
    path = tmp_path / 'input.png'
    Image.new('RGBA', (128, 128), (0, 0, 0, 0)).save(path)
    parser = Path(__file__).resolve().parents[2] / 'docker' / 'attachment-parser.py'
    def run(limit, mime):
        return subprocess.run([sys.executable, str(parser), str(path), '--model-image', str(limit), mime], capture_output=True)
    assert json.loads(run(3000, 'image/png').stdout) == {'mime': 'image/png'}
    assert json.loads(run(3000, 'image/jpeg').stdout) == {'mime': 'image/jpeg', 'converted': True}
    with Image.open(tmp_path / 'model-image') as converted:
        assert converted.format == 'JPEG' and converted.getpixel((0, 0)) == (255, 255, 255)
    assert run(1, 'image/jpeg').returncode != 0


@pytest.mark.parametrize('output', ['not JSON', '{"text": ""}', '{"text": 123}'])
def test_invalid_parser_output_fails_and_always_destroys_environment(monkeypatch, output):
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=0, logs=ExecutionLogs(
        stdout=[OutputMessage(text=output, timestamp=0)]))
    monkeypatch.setattr('opensandbox.SandboxSync.create', Mock(return_value=native))
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: None)
    with pytest.raises((StoreError, ValueError)):
        _parse_attachment('document.pdf', b'untrusted')
    native.destroy.assert_called_once()


def test_parser_command_failure_is_not_retried_or_parsed_on_host(monkeypatch):
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=1,
        error=ExecutionError(name='ParserError', value='bad format', timestamp=0, exit_code=1))
    create = Mock(return_value=native)
    monkeypatch.setattr('opensandbox.SandboxSync.create', create)
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: None)
    with pytest.raises(StoreError, match='隔离附件解析失败'):
        _parse_attachment('document.pdf', b'untrusted')
    create.assert_called_once()
    native.commands.run.assert_called_once()
    native.destroy.assert_called_once()


def test_image_validation_uses_same_sandbox_and_returns_only_supported_mime(monkeypatch):
    native = Mock()
    native.commands.run.return_value = Execution(exit_code=0, logs=ExecutionLogs(
        stdout=[OutputMessage(text='{"mime":"image/png"}', timestamp=0)]))
    monkeypatch.setattr('opensandbox.SandboxSync.create', Mock(return_value=native))
    monkeypatch.setattr('agent.sandbox.connection_config', lambda: None)
    assert _image_mime('disguised.txt', b'image bytes') == 'image/png'
    assert native.commands.run.call_args.args[0] == ['python', '/opt/attachment-parser.py', '/tmp/input.txt', '--image']
    native.commands.run.return_value = Execution(exit_code=0, logs=ExecutionLogs(
        stdout=[OutputMessage(text='{"mime":"image/bmp"}', timestamp=0)]))
    with pytest.raises(StoreError) as rejected:
        _image_mime('unsupported.bmp', b'unsupported')
    assert rejected.value.status == 400
    assert native.destroy.call_count == 2


@pytest.mark.skipif(os.getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox and the fixed parser image')
def test_real_image_validation_detects_mime_and_rejects_invalid_bytes(monkeypatch):
    from dotenv import dotenv_values
    from PIL import Image
    for key, value in dotenv_values('.env').items():
        if key.startswith('OPEN_SANDBOX_') and value:
            monkeypatch.setenv(key, value)
    content = io.BytesIO()
    Image.new('RGB', (2, 2), 'white').save(content, 'PNG')
    assert _image_mime('wrong-extension.jpeg', content.getvalue()) == 'image/png'
    with pytest.raises(StoreError) as invalid:
        _image_mime('invalid.png', b'invalid image')
    assert invalid.value.status == 422


@pytest.mark.skipif(os.getenv('OPEN_SANDBOX_TEST_REAL') != '1', reason='requires local OpenSandbox and the fixed parser image')
@pytest.mark.parametrize('extension', ['txt', 'docx', 'pptx', 'xlsx', 'pdf', 'scan.pdf'])
def test_real_isolated_parser_preserves_supported_document_text(monkeypatch, extension):
    from dotenv import dotenv_values
    settings = dotenv_values('.env')
    for key in ('OPEN_SANDBOX_API_KEY', 'OPEN_SANDBOX_DOMAIN', 'OPEN_SANDBOX_PROTOCOL'):
        if settings.get(key):
            monkeypatch.setenv(key, settings[key])
    content = io.BytesIO()
    if extension == 'txt':
        content.write(b'Parser fixture')
    elif extension == 'docx':
        from docx import Document
        document = Document()
        document.add_paragraph('Parser fixture')
        document.save(content)
    elif extension == 'pptx':
        from pptx import Presentation
        document = Presentation()
        slide = document.slides.add_slide(document.slide_layouts[5])
        slide.shapes.title.text = 'Parser fixture'
        document.save(content)
    elif extension == 'xlsx':
        from openpyxl import Workbook
        document = Workbook()
        document.active.append(['Parser fixture'])
        document.save(content)
        document.close()
    elif extension == 'scan.pdf':
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new('RGB', (1000, 400), 'white')
        ImageDraw.Draw(image).text((60, 150), 'Parser fixture', fill='black', font=ImageFont.load_default(size=48))
        image.save(content, format='PDF', resolution=150)
    else:
        stream = b'BT /F1 12 Tf 10 50 Td (Parser fixture) Tj ET'
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
                   b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
        content.write(b'%PDF-1.4\n')
        offsets = [0]
        for index, value in enumerate(objects, 1):
            offsets.append(content.tell())
            content.write(str(index).encode() + b' 0 obj\n' + value + b'\nendobj\n')
        position = content.tell()
        content.write(b'xref\n0 6\n0000000000 65535 f \n')
        for offset in offsets[1:]:
            content.write(f'{offset:010d} 00000 n \n'.encode())
        content.write(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{position}\n%%EOF'.encode())
    assert 'Parser fixture' in _parse_attachment('fixture.' + extension, content.getvalue())
