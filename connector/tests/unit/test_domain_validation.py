import pytest

from spiderfoot_connector.allowlist import validate_domain


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "example.com"),
        ("  WWW.Example.COM.  ", "www.example.com"),
        ("sub.domain.example.org", "sub.domain.example.org"),
        ("a-b.example.com", "a-b.example.com"),
        ("123.example.com", "123.example.com"),
        ("xn--bcher-kva.example", "xn--bcher-kva.example"),
        ("example.co.uk", "example.co.uk"),  # a registrable name under a multi-part suffix
        ("forocoches.com", "forocoches.com"),
    ],
)
def test_valid_names_are_accepted_and_normalised(raw, expected):
    assert validate_domain(raw) == expected


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("com", "at least two"),
        ("localhost", "at least two"),
        ("co.uk", "public suffix"),
        ("com.au", "public suffix"),
        ("github.io", "public suffix"),
        ("blogspot.com", "public suffix"),
        ("192.168.0.1", "IP address"),
        ("8.8.8.8", "IP address"),
        ("::1", "IP address"),
        ("http://example.com", "scheme"),
        ("https://example.com/path", "scheme"),
        ("example.com/path", "path"),
        ("example.com:8080", "port"),
        ("*.example.com", "wildcard"),
        ("exa mple.com", "whitespace"),
        ("user@example.com", "valid host name"),
        ("-bad.example.com", "valid host name"),
        ("bad-.example.com", "valid host name"),
        (".example.com", "valid host name"),
        ("example..com", "valid host name"),
        ("under_score.example.com", "valid host name"),
        ("example.123", "valid host name"),
        ("a" * 64 + ".example.com", "valid host name"),
        (("a" * 60 + ".") * 5 + "com", "too long"),
    ],
)
def test_unsafe_or_malformed_names_are_refused_with_a_reason(raw, reason):
    with pytest.raises(ValueError) as err:
        validate_domain(raw)
    assert reason in str(err.value)


def test_a_bare_top_level_name_would_authorise_every_domain_under_it_so_it_is_refused():
    from spiderfoot_connector.allowlist import is_allowed

    # the reason validation exists: this is what an unvalidated "com" would do
    assert is_allowed("anyone-else.com", frozenset({"com"}))
    with pytest.raises(ValueError):
        validate_domain("com")
