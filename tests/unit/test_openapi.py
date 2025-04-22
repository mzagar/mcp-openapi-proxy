import pytest
import os
from mcp_openapi_proxy import openapi

def test_fetch_openapi_spec_json(monkeypatch, tmp_path):
    file_path = tmp_path / "spec.json"
    file_path.write_text('{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}, "paths": {}}')
    spec = openapi.fetch_openapi_spec(f"file://{file_path}")
    assert isinstance(spec, dict)
    assert spec["openapi"] == "3.0.0"

def test_fetch_openapi_spec_yaml(monkeypatch, tmp_path):
    file_path = tmp_path / "spec.yaml"
    file_path.write_text('openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0\npaths: {}')
    monkeypatch.setenv("OPENAPI_SPEC_FORMAT", "yaml")
    spec = openapi.fetch_openapi_spec(f"file://{file_path}")
    assert isinstance(spec, dict)
    assert spec["openapi"] == "3.0.0"
    monkeypatch.delenv("OPENAPI_SPEC_FORMAT", raising=False)

def test_fetch_openapi_spec_json_decode_error(monkeypatch, tmp_path):
    file_path = tmp_path / "spec.json"
    file_path.write_text("{invalid json}")
    spec = openapi.fetch_openapi_spec(f"file://{file_path}")
    # Accept None or YAML fallback result (dict with one key and value None)
    assert spec is None or (isinstance(spec, dict) and list(spec.values()) == [None])

def test_fetch_openapi_spec_yaml_decode_error(monkeypatch, tmp_path):
    file_path = tmp_path / "spec.yaml"
    file_path.write_text(": : :")
    monkeypatch.setenv("OPENAPI_SPEC_FORMAT", "yaml")
    spec = openapi.fetch_openapi_spec(f"file://{file_path}")
    assert spec is None
    monkeypatch.delenv("OPENAPI_SPEC_FORMAT", raising=False)

def test_build_base_url_servers(monkeypatch):
    monkeypatch.delenv("SERVER_URL_OVERRIDE", raising=False)
    spec = {"servers": [{"url": "https://api.example.com"}]}
    url = openapi.build_base_url(spec)
    assert url == "https://api.example.com"

def test_build_base_url_host_schemes(monkeypatch):
    monkeypatch.delenv("SERVER_URL_OVERRIDE", raising=False)
    spec = {"host": "api.example.com", "schemes": ["https"], "basePath": "/v1"}
    url = openapi.build_base_url(spec)
    assert url == "https://api.example.com/v1"

def test_build_base_url_override(monkeypatch):
    monkeypatch.setenv("SERVER_URL_OVERRIDE", "https://override.example.com")
    url = openapi.build_base_url({})
    assert url == "https://override.example.com"
    monkeypatch.delenv("SERVER_URL_OVERRIDE", raising=False)

def test_build_base_url_override_invalid(monkeypatch):
    monkeypatch.setenv("SERVER_URL_OVERRIDE", "not_a_url")
    url = openapi.build_base_url({})
    assert url is None
    monkeypatch.delenv("SERVER_URL_OVERRIDE", raising=False)

def test_handle_auth_bearer(monkeypatch):
    monkeypatch.setenv("API_KEY", "bearer_token")
    monkeypatch.setenv("API_AUTH_TYPE", "bearer")
    headers = openapi.handle_auth({})
    assert headers["Authorization"].startswith("Bearer ")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_AUTH_TYPE", raising=False)

def test_handle_auth_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "api_key_value")
    monkeypatch.setenv("API_AUTH_TYPE", "api-key")
    monkeypatch.setenv("API_AUTH_HEADER", "X-API-KEY")
    headers = openapi.handle_auth({})
    assert headers.get("X-API-KEY") == "api_key_value"
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_AUTH_TYPE", raising=False)
    monkeypatch.delenv("API_AUTH_HEADER", raising=False)

def test_handle_auth_basic(monkeypatch):
    monkeypatch.setenv("API_KEY", "basic_key")
    monkeypatch.setenv("API_AUTH_TYPE", "basic")
    headers = openapi.handle_auth({})
    assert isinstance(headers, dict)
    assert "Authorization" not in headers
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_AUTH_TYPE", raising=False)

def test_lookup_operation_details():
    from mcp_openapi_proxy.utils import normalize_tool_name
    spec = {
        "paths": {
            "/foo": {
                "get": {"operationId": "getFoo"}
            },
            "/bar": {
                "post": {"operationId": "postBar"}
            }
        }
    }
    fn = normalize_tool_name("GET /foo")
    details = openapi.lookup_operation_details(fn, spec)
    assert details is not None
    assert details["path"] == "/foo"
    fn2 = normalize_tool_name("POST /bar")
    details2 = openapi.lookup_operation_details(fn2, spec)
    assert details2 is not None
    assert details2["path"] == "/bar"
    assert openapi.lookup_operation_details("not_a_func", spec) is None
