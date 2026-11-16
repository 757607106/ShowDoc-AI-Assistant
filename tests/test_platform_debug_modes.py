"""Debug input validation and the original embedding similarity response."""
import io
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent import registry
from webapi import model_runtime


def saved_model(kind='Embedding'):
    return registry.save_model({'name': 'debug-fixture', 'type': kind,
        'parameters': {'provider': 'generic', 'base_url': 'https://fixture.invalid/v1'}},
        os.environ['TEST_PLATFORM_USER'])


def vectors(*values):
    return SimpleNamespace(data=[{'index': index, 'embedding': value} for index, value in enumerate(values)])


def test_embedding_similarity_keeps_candidate_indices_and_stable_ties(authenticated_client, monkeypatch):
    model = saved_model()
    candidates = vectors([-1, 0], [1, 0], [1, 0], [0, 0])
    candidates.data.reverse()
    embed = Mock(side_effect=[vectors([1, 0]), candidates])
    monkeypatch.setattr(model_runtime, 'embed_model', embed)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", json={
        'input': 'query', 'documents': ['opposite', 'first tie', 'second tie', 'zero'],
        'options': {'similarity': True}})
    assert response.status_code == 200 and response.json['data']['ok'], response.json
    result = response.json['data']
    assert result['raw_response']['results'] == [
        {'index': 1, 'kind': 'text', 'content': 'first tie', 'similarity': 1},
        {'index': 2, 'kind': 'text', 'content': 'second tie', 'similarity': 1},
        {'index': 3, 'kind': 'text', 'content': 'zero', 'similarity': 0},
        {'index': 0, 'kind': 'text', 'content': 'opposite', 'similarity': -1},
    ]
    assert result['observations']['dimension'] == 2 and result['observations']['result_count'] == 4
    assert [call.args[1] for call in embed.call_args_list] == [
        ['query'], ['opposite', 'first tie', 'second tie', 'zero']]


@pytest.mark.parametrize('query,candidates', [
    (vectors(), vectors([1, 0], [0, 1])),
    (vectors([1, 0]), vectors([1, 0])),
    (vectors([1, 0]), vectors([1, 0, 0], [0, 1])),
    (vectors([1, 0]), vectors([float('nan'), 0], [0, 1])),
    (vectors([1, 0]), SimpleNamespace(data=[
        {'index': 0, 'embedding': [1, 0]}, {'index': 0, 'embedding': [0, 1]}])),
])
def test_embedding_similarity_rejects_invalid_provider_vectors(authenticated_client, monkeypatch, query, candidates):
    model = saved_model()
    monkeypatch.setattr(model_runtime, 'embed_model', Mock(side_effect=[query, candidates]))
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", json={
        'input': 'query', 'documents': ['first', 'second'], 'options': {'similarity': True}})
    assert response.status_code == 200
    result = response.json['data']
    assert result['ok'] is False and result['raw_response'] is None and result['error']
    assert 'results' not in result['observations']


@pytest.mark.parametrize('body', [
    {'input': '', 'documents': ['candidate'], 'options': {'similarity': True}},
    {'input': 'query', 'documents': [], 'options': {'similarity': True}},
    {'input': 'query', 'documents': '{', 'options': {'similarity': True}},
    {'input': 'query', 'documents': [3], 'options': {'similarity': True}},
    {'input': 'query', 'documents': ['candidate'] * 101, 'options': {'similarity': True}},
    {'input': 'query', 'documents': ['candidate'], 'options': {'similarity': 'yes'}},
])
def test_invalid_similarity_inputs_do_not_call_provider(authenticated_client, monkeypatch, body):
    model = saved_model()
    embed = Mock(side_effect=AssertionError('Invalid input must not call the model'))
    monkeypatch.setattr(model_runtime, 'embed_model', embed)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", json=body)
    assert response.status_code == 400, response.json
    embed.assert_not_called()


@pytest.mark.parametrize('kind', ['Embedding', 'Rerank'])
def test_unconnected_nonchat_image_modes_fail_before_provider(authenticated_client, monkeypatch, kind):
    model = saved_model(kind)
    embed, rerank = Mock(), Mock()
    monkeypatch.setattr(model_runtime, 'embed_model', embed)
    monkeypatch.setattr(model_runtime, 'rerank_model', rerank)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'input': 'query', 'documents': '["candidate"]', 'options': '{}',
        'file': (io.BytesIO(b'unsupported-image-mode'), 'image.png')})
    assert response.status_code == 501, response.json
    embed.assert_not_called()
    rerank.assert_not_called()


def test_empty_asr_upload_does_not_call_provider(authenticated_client, monkeypatch):
    model = saved_model('ASR')
    transcribe = Mock()
    monkeypatch.setattr(model_runtime, 'transcribe_model', transcribe)
    response = authenticated_client.post(f"/api/v1/models/{model['id']}/debug", data={
        'options': '{}', 'file': (io.BytesIO(), 'empty.wav')})
    assert response.status_code == 413, response.json
    transcribe.assert_not_called()
