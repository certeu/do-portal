from app import utils


def test_email_validation():
    assert utils.is_valid_email('cert-eu@ec.europa.eu')
    assert utils.is_valid_email('ec.europa.eu') is False


def test_add_slasshes():
    assert utils.addslashes('{"key": "val"}') == '{\\"key\\": \\"val\\"}'


def test_calc_hashes():
    digests = utils.get_hashes(b'42')
    assert digests.md5 == 'a1d0c6e83f027327d8461063f4ac58a6'
    assert digests.sha1 == '92cfceb39d57d914ed8b14d0e37643de0797ae56'
    assert digests.sha256 == \
        '73475cb40a568e8da8a045ced110137e159f890ac4da883b6b17dc651b3a8049'
