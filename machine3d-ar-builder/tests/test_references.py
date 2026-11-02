from machine3d.references import allowed_license


def test_allowed_licenses():
    assert allowed_license("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")
    assert allowed_license("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/")
    assert allowed_license("CC0", "https://creativecommons.org/publicdomain/zero/1.0/")
    assert allowed_license("Public domain", "")


def test_restricted_and_unknown_licenses_rejected():
    assert not allowed_license("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/")
    assert not allowed_license("CC BY-ND 4.0", "")
    assert not allowed_license("All rights reserved", "")
