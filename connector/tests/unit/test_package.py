import spiderfoot_connector


def test_package_exposes_version():
    assert spiderfoot_connector.__version__ == "0.1.0"
