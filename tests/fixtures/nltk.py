"""NLTK fixtures that keep the downloader off the network during tests.

``aidial_rag_eval`` calls ``nltk.download("punkt_tab", quiet=True)`` on every
text segmentation. Since nltk 3.10.0 the downloader routes all network access
through ``nltk.pathsec`` (a security-hardening module using a custom
``_SafeHTTPSConnection``). That connection class is incompatible with vcrpy's
monkeypatched ``HTTPSConnection`` and raises a ``TypeError`` whenever a download
is attempted inside an active cassette, which the metrics swallow into an error
result. See tests/cassettes.md for cassette details.

This fixture pre-seeds the required nltk data once at session start (before any
cassette is active) and then replaces ``nltk.download`` with a no-op for the
rest of the session, so no connection is ever opened during a recorded test.
"""

import nltk
import nltk.data
import pytest

# nltk data packages the test suite relies on (via aidial_rag_eval segmentation),
# mapped to the resource path used to detect whether they are already installed.
_REQUIRED_NLTK_DATA = {
    "punkt_tab": "tokenizers/punkt_tab",
}


def _noop_download(*_args, **_kwargs) -> bool:
    return True


@pytest.fixture(scope="session", autouse=True)
def preseed_nltk_data():
    """Ensure nltk data is present, then block network downloads for the session.

    Runs before any test opens a VCR cassette, so the one-time download (only
    when data is missing) uses the real network safely. Afterwards
    ``nltk.download`` is a no-op, preventing the nltk 3.10.0 secure downloader
    from clashing with vcrpy's connection patching mid-test.
    """
    download = getattr(nltk, "download")
    for package, data_path in _REQUIRED_NLTK_DATA.items():
        try:
            nltk.data.find(data_path)
        except LookupError:
            download(package, quiet=True)

    setattr(nltk, "download", _noop_download)
    try:
        yield
    finally:
        setattr(nltk, "download", download)
