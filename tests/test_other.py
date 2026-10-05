import pytest

pytestmark = [
    pytest.mark.T1,
    pytest.mark.T2,
    pytest.mark.T3,
    pytest.mark.T4,
    pytest.mark.T5,
    pytest.mark.T6,
    pytest.mark.T7,
    pytest.mark.T8,
    pytest.mark.T9,
    pytest.mark.T10,
    pytest.mark.T11,
    pytest.mark.T12,
    pytest.mark.T13,
    pytest.mark.T14,
]


def test_all_marked():
    assert True
