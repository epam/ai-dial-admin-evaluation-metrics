"""Integration test that the tiktoken download host is blocked by VCR."""

import pytest
import requests


@pytest.mark.vcr
def test_tiktoken_request_is_blocked():
    """A tiktoken download request must be blocked by the VCR config."""
    url = "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
    with pytest.raises(RuntimeError, match="blocked in tests"):
        requests.get(url)
