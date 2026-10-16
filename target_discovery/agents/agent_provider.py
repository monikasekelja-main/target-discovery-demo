"""Minimal Responses API transport; no SDK dependency, implicit tools or automatic retries."""
import json
import os
import urllib.error
import urllib.request

class ProviderError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class OpenAIProvider:
    mode = 'live_llm'
    def __init__(self, model, *, timeout=120, max_output_tokens=4000):
        if not model or not model.strip():
            raise ProviderError('Live mode requires --model with a Structured Outputs compatible model available to your account.')
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.key = os.environ.get('OPENAI_API_KEY')
        if not self.key:
            raise ProviderError('Set OPENAI_API_KEY locally; never paste your key into a report or chat.')

    def complete(self, role, instructions, payload, schema):
        body = {'model': self.model, 'store': False, 'instructions': instructions,
                'input': json.dumps(payload, ensure_ascii=False, allow_nan=False),
                'max_output_tokens': self.max_output_tokens,
                'text': {'format': {'type': 'json_schema', 'name': role,
                                    'strict': True, 'schema': schema}}}
        request = urllib.request.Request('https://api.openai.com/v1/responses',
            data=json.dumps(body).encode(), headers={'Authorization': 'Bearer '+self.key,
            'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError('Provider response exceeded size limit.')
            data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Do not print provider bodies/headers or credentials.
            raise ProviderError(f'Provider HTTP {exc.code}; no automatic retry or fallback. Check model access, quota and schema compatibility.') from None
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise ProviderError('Provider connection/response failure; no automatic retry or fallback.') from None
        if not isinstance(data, dict):
            raise ProviderError('Malformed provider response.')
        if data.get('status') != 'completed':
            raise ProviderError('Provider did not complete (possibly output budget); no partial output accepted.')
        parts = []
        items = data.get('output')
        if not isinstance(items, list):
            raise ProviderError('Malformed provider output.')
        for item in items:
            if not isinstance(item, dict):
                raise ProviderError('Malformed provider output item.')
            if item.get('type') != 'message':
                continue
            contents = item.get('content')
            if not isinstance(contents, list):
                raise ProviderError('Malformed provider message.')
            for content in contents:
                if not isinstance(content, dict):
                    raise ProviderError('Malformed provider content.')
                if content.get('type') == 'refusal':
                    raise ProviderError('Model refused; no output accepted.')
                if content.get('type') == 'output_text':
                    if not isinstance(content.get('text'), str):
                        raise ProviderError('Malformed provider output text.')
                    parts.append(content['text'])
        try:
            value = json.loads(''.join(parts))
        except (ValueError, TypeError):
            raise ProviderError('Provider returned no valid JSON output.') from None
        return value, {'response_id': data.get('id'), 'resolved_model': data.get('model'),
                       'usage': data.get('usage'), 'mode': self.mode}
