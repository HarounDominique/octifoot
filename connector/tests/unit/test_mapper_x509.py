from datetime import UTC, datetime

from spiderfoot_connector.mapper import IMPORTED_EVENTS, map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


def cert(serial="17:db:50:1d:c5:d3:b4:31", cn="example.com", not_before="Sep 27 09:29:10 2026 GMT"):
    return (
        "Certificate:\n"
        "    Data:\n"
        "        Version: 3 (0x2)\n"
        "        Serial Number:\n"
        f"            {serial}\n"
        "        Signature Algorithm: ecdsa-with-SHA256\n"
        "        Issuer: C=US, O=Example Trust Services, CN=WE1\n"
        "        Validity\n"
        f"            Not Before: {not_before}\n"
        "            Not After : Dec 26 10:28:56 2026 GMT\n"
        f"        Subject: CN={cn}\n"
        "        Subject Public Key Info:\n"
        "            Public Key Algorithm: id-ecPublicKey\n"
        "                pub:\n"
        "                    04:d0:4f:43\n"
        "        X509v3 extensions:\n"
        "            X509v3 Key Usage: critical\n"
        "                Digital Signature\n"
        "            X509v3 Extended"
    )


def run(events, target="example.com"):
    return map_events(events, target=target, scan_id="S1", score=30, now=NOW)


def ev(data, source="example.com", etype="SSL_CERTIFICATE_RAW"):
    return {
        "event_type": etype,
        "data": data,
        "source_data": source,
        "module": "sfp_crt",
        "false_positive": 0,
    }


def certs(result):
    return [o for o in result.objects if o.type == "x509-certificate"]


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def test_certificate_fields_are_parsed_into_a_stix_object():
    (c,) = certs(run([ev(cert())]))
    assert c.serial_number == "17:db:50:1d:c5:d3:b4:31"
    assert c.signature_algorithm == "ecdsa-with-SHA256"
    assert c.issuer == "C=US, O=Example Trust Services, CN=WE1"
    assert c.subject == "CN=example.com"
    assert c.validity_not_before == datetime(2026, 9, 27, 9, 29, 10, tzinfo=UTC)
    assert c.validity_not_after == datetime(2026, 12, 26, 10, 28, 56, tzinfo=UTC)


def test_certificate_is_related_to_the_scanned_domain_with_provenance():
    r = run([ev(cert())])
    (c,) = certs(r)
    target = next(o for o in r.objects if o.type == "domain-name" and o.value == "example.com")
    rels = [o for o in r.objects if o.type == "relationship" and o.source_ref == c.id]
    assert [(x.relationship_type, x.target_ref) for x in rels] == [("related-to", target.id)]
    refs = c.x_opencti_external_references
    assert refs[0]["source_name"] == "SpiderFoot" and refs[0]["external_id"] == "S1"
    assert "sfp_crt" in refs[0]["description"]


def test_wildcard_and_names_under_the_target_are_accepted():
    for cn in ("*.example.com", "api.example.com", "EXAMPLE.com"):
        assert len(certs(run([ev(cert(cn=cn))]))) == 1, cn


def test_parent_domain_certificate_is_accepted_for_a_subdomain_target():
    assert (
        len(certs(run([ev(cert(cn="example.com"), source="www.example.com")], "www.example.com")))
        == 1
    )


def test_certificate_for_another_name_is_not_imported_and_is_counted():
    for cn in ("other.net", "notexample.com", "example.com.evil.net", "sibling.example.com"):
        r = run([ev(cert(cn=cn))], target="www.example.com")
        assert not certs(r), cn
        assert r.unmapped["SSL_CERTIFICATE_RAW (not the target's)"] == 1, cn


def test_names_never_become_domain_objects():
    r = run([ev(cert(cn="*.example.com"))])
    assert {o.value for o in r.objects if o.type == "domain-name"} == {"example.com"}


def test_truncated_text_still_parses_what_arrived():
    assert len(certs(run([ev(cert()[:420])]))) == 1


def test_certificate_without_serial_or_subject_is_invalid():
    r = run([ev("Certificate:\n    Data:\n        Version: 3 (0x2)\n")])
    assert not certs(r) and r.invalid == 1
    assert run([ev(cert().replace("Subject: CN=example.com", "Subject:"))]).invalid == 1


def test_the_same_serial_is_imported_once():
    assert len(certs(run([ev(cert()), ev(cert())]))) == 1


def test_at_most_ten_most_recent_certificates_are_imported_and_the_rest_counted():
    events = [
        ev(cert(serial=f"00:{i:02d}", not_before=f"Jan {i:02d} 00:00:00 2026 GMT"))
        for i in range(1, 13)
    ]
    r = run(events)
    serials = {c.serial_number for c in certs(r)}
    assert len(serials) == 10
    assert (
        "00:12" in serials
        and "00:03" in serials
        and "00:02" not in serials
        and "00:01" not in serials
    )
    assert "TLS certificates: 10 imported, 2 over the cap of 10" in note(r)


def test_note_line_reports_counts_and_what_was_not_the_targets():
    r = run([ev(cert()), ev(cert(serial="00:99", cn="other.net"))])
    assert (
        "TLS certificates: 1 imported, 0 over the cap of 10, 1 not issued for the target" in note(r)
    )


def test_no_certificates_means_no_line():
    assert "TLS certificates" not in note(run([ev("x", etype="INTERNET_NAME")]))


def test_other_ids_are_unchanged_and_output_is_deterministic():
    base = {o.id for o in run([]).objects if o.type not in ("note",)}
    withcert = run([ev(cert())])
    assert base <= {o.id for o in withcert.objects}
    again = run([ev(cert())])
    assert sorted(o.id for o in withcert.objects) == sorted(o.id for o in again.objects)
    assert note(withcert) == note(again)


def test_declared_as_imported():
    assert "SSL_CERTIFICATE_RAW" in IMPORTED_EVENTS
