from types import SimpleNamespace

from app.mcp_client import MCPToolClient


def test_mcp_decoder_prefers_structured_content():
    result = SimpleNamespace(
        isError=False,
        structuredContent={
            "items": [{"document_id": "EPMC:MED:123", "title": "Paper"}],
            "source_status": {"europe_pmc": {"ok": True}},
        },
        content=[],
    )

    decoded = MCPToolClient._decode_result(result)

    assert decoded["items"][0]["document_id"] == "EPMC:MED:123"
    assert decoded["source_status"]["europe_pmc"]["ok"] is True


def test_mcp_decoder_supports_snake_case_structured_content():
    result = SimpleNamespace(
        isError=False,
        structuredContent=None,
        structured_content={"items": [{"document_id": "DOC001"}]},
        content=[],
    )

    decoded = MCPToolClient._decode_result(result)

    assert decoded["items"][0]["document_id"] == "DOC001"


def test_mcp_decoder_falls_back_to_json_text_for_legacy_servers():
    result = SimpleNamespace(
        isError=False,
        structuredContent=None,
        structured_content=None,
        content=[SimpleNamespace(type="text", text='{"items": [{"document_id": "DOC002"}]}')],
    )

    decoded = MCPToolClient._decode_result(result)

    assert decoded["items"][0]["document_id"] == "DOC002"
