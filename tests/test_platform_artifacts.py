"""Archived image attachments retain owned previews."""
import io
import base64
import os
from PIL import Image
from agent import sessions


def test_image_upload_history_uses_owned_preview_and_not_base64(authenticated_client):
    from webapi.chat_resources import prepare_attachments
    owner = os.environ['TEST_PLATFORM_USER']
    sid = sessions.create_session(owner_id=owner)['id']
    raw = io.BytesIO()
    Image.new('RGB', (2, 2), 'white').save(raw, 'PNG')
    value = prepare_attachments(sid, owner, {'images': [{'data': 'data:image/png;base64,' + base64.b64encode(raw.getvalue()).decode()}]})
    image = value['user_images'][0]
    assert 'base64' not in image['url'] and image['id'] in value['attachment_ids']
    assert authenticated_client.get(image['url']).data == raw.getvalue()

