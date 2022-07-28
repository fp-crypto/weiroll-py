from brownie.convert import to_bytes
from hexbytes import HexBytes
import random
from brownie import reverts

b2 = to_bytes(2)
b1 = to_bytes(1)
b4 = to_bytes(4)


def test_insert(tuple_helper):

    assert (
        HexBytes(
            tuple_helper.insertElement.transact(b2 + b1, 0, b4, False).return_value
        )
        == b4 + b2 + b1
    )
    assert (
        HexBytes(
            tuple_helper.insertElement.transact(b2 + b1, 1, b4, False).return_value
        )
        == b2 + b4 + b1
    )
    assert (
        HexBytes(
            tuple_helper.insertElement.transact(b2 + b1, 2, b4, False).return_value
        )
        == b2 + b1 + b4
    )

    with reverts():
        tuple_helper.insertElement.transact(b2 + b1, 3, b4, False)

    rands = HexBytes(
        b"".join([to_bytes(random.randint(0, 2 ** 256 - 1)) for _ in range(100)])
    )

    for i in range(101):
        r = HexBytes(
            tuple_helper.insertElement.transact(rands, i, b4, False).return_value
        )
        inserted = HexBytes(rands[: i * 32] + HexBytes(b4) + rands[i * 32 :])
        assert r == inserted


def test_replace(tuple_helper):

    assert (
        HexBytes(
            tuple_helper.replaceElement.transact(b2 + b1, 0, b4, False).return_value
        )
        == b4 + b1
    )
    assert (
        HexBytes(
            tuple_helper.replaceElement.transact(b2 + b1, 1, b4, False).return_value
        )
        == b2 + b4
    )

    with reverts():
        tuple_helper.replaceElement.transact(b2 + b1, 2, b4, False)

    rands = HexBytes(
        b"".join([to_bytes(random.randint(0, 2 ** 256 - 1)) for _ in range(100)])
    )

    for i in range(100):
        r = HexBytes(
            tuple_helper.replaceElement.transact(rands, i, b4, False).return_value
        )
        inserted = HexBytes(rands[: i * 32] + HexBytes(b4) + rands[(i + 1) * 32 :])
        assert r == inserted
