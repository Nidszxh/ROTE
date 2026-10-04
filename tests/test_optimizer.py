import pytest

pytestmark = [
    pytest.mark.T1,
    pytest.mark.T2,
    pytest.mark.T3,
    pytest.mark.T4,
    pytest.mark.T5,
    pytest.mark.T6,
    pytest.mark.T7,
    pytest.mark.T11,
]


def test_placeholder():
    assert True
