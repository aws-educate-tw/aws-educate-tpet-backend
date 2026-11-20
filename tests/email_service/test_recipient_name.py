import pytest

from email_service.create_email.data_util import map_recipient_name


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"Name": " Amy ", "姓名": "小美"}, "Amy"),
        ({"姓名": " 小美 "}, "小美"),
        ({"Name": "  ", "姓名": "小美"}, "小美"),
        ({"Name": float("nan"), "姓名": "小美"}, "小美"),
        ({"Name": None, "姓名": "  "}, None),
        ({"Email": "guest@example.test"}, None),
    ],
)
def test_name_from_recipient_row(row, expected):
    assert map_recipient_name(row) == expected
