from brownie import Contract, accounts, Wei, chain, TestableVM, convert
from brownie.convert.datatypes import HexString

import weiroll
from weiroll import WeirollContract, WeirollPlanner, ReturnValue, CommandFlags
import requests


def test_one_inch(weiroll_vm):
    whale = accounts.at(
        "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True
    )
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")

    weth.transfer(weiroll_vm.address, Wei("10 ether"), {"from": whale})

    swap_url = "https://api.1inch.io/v4.0/1/swap"
    r = requests.get(
        swap_url,
        params={
            "fromTokenAddress": weth.address,
            "toTokenAddress": crv.address,
            "amount": Wei("10 ether"),
            "fromAddress": weiroll_vm.address,
            "slippage": 5,
            "disableEstimate": "true",
            "allowPartialFill": "false",
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    weth.approve(one_inch, 2**256 - 1, {"from": weiroll_vm, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]

    planner = WeirollPlanner(weiroll_vm)
    planner.call(one_inch, func_name, *params)

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(weiroll_vm) > 0


def test_one_inch_replace_calldata_amount():
    whale = accounts.at(
        "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True
    )
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")
    th = Contract("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b")
    ms = accounts.at("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6", force=True)

    weth.transfer(th.address, Wei("10 ether"), {"from": whale})

    swap_url = "https://api.1inch.io/v4.0/1/swap"
    r = requests.get(
        swap_url,
        params={
            "fromTokenAddress": weth.address,
            "toTokenAddress": crv.address,
            "amount": Wei("10 ether"),
            "fromAddress": th.address,
            "slippage": 5,
            "disableEstimate": "true",
            "allowPartialFill": "false",
            "usePatching": "true",
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    weth.approve(one_inch, 2**256 - 1, {"from": th, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]

    # change inputs
    wei9 = Wei("9 ether")
    params[1][4] = wei9
    params[1][5] = 1

    planner = WeirollPlanner(th)
    # w_one_inch = weiroll.WeirollContract(one_inch)
    # print(f'{func_name}\n{params}')
    # planner.add(w_one_inch.swap(params[0], params[1], params[2]))
    planner.call(one_inch, func_name, *params)

    cmds, state = planner.plan()
    print(f"cmds: {cmds}")
    print(f"state: {state}")

    weiroll_tx = th.execute(
        cmds, state, {"from": ms, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(th) > 0
    print(crv.balanceOf(th))
    assert weth.balanceOf(th) == 1 * 10**18
    assert False


def test_one_inch_replace_calldata_amount_2(weiroll_vm):
    whale = accounts.at(
        "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True
    )
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")

    weth.transfer(weiroll_vm.address, Wei("10 ether"), {"from": whale})

    swap_url = "https://api.1inch.io/v4.0/1/swap"
    r = requests.get(
        swap_url,
        params={
            "fromTokenAddress": weth.address,
            "toTokenAddress": crv.address,
            "amount": Wei("10 ether"),
            "fromAddress": weiroll_vm.address,
            "slippage": 5,
            "disableEstimate": "true",
            "allowPartialFill": "false",
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    weth.approve(one_inch, 2**256 - 1, {"from": weiroll_vm, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]
    calldata = params[2]

    # change inputs
    wei9 = Wei("9 ether")

    # testing with calldata amount < struct amount at 10 wei still
    # params[1][4] = wei9
    params[1][5] = 1

    # Operations to edit decoded swap data
    # convert dec to hex (0xHexDec) -> (0x00...HexDec) -> (00..HexDec) string
    hex10 = HexString(hex(Wei("10 ether")), "bytes32").hex()
    hex9 = HexString(hex(wei9), "bytes32").hex()

    # HexString to string
    calldata_str = calldata.hex()

    # string replacement
    replaced = calldata_str.replace(hex10, hex9)

    # back to hexstring
    params[2] = HexString(replaced, "bytes")

    planner = WeirollPlanner(weiroll_vm)
    planner.call(one_inch, func_name, *params)

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(weiroll_vm) > 0
    print(crv.balanceOf(weiroll_vm))


import re
import eth_abi
from brownie import Contract, accounts, Wei, chain, TestableVM, convert
from brownie.convert.datatypes import HexString
import weiroll
from weiroll import WeirollContract, WeirollPlanner, ReturnValue
import requests

# def test_a_b():
#     cmds, staste = test_one_inch_replace_calldata_with_weiroll(True)
#     cmds2, staste2 = test_one_inch_replace_calldata_with_weiroll(False)
#
#     assert False


def test_one_inch_replace_amount_with_weiroll(router_like):
    whale = accounts.at(
        "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True
    )
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")
    tuple_helper = Contract("0x06706E366159cEfD3789184686da5cC3f47fB4a2")
    w_tuple_helper = weiroll.WeirollContract(tuple_helper, CommandFlags.CALL)
    th = Contract("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b")
    ms = accounts.at("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6", force=True)
    planner = WeirollPlanner(th)

    weth.approve(th.address, Wei("9 ether"), {"from": whale})
    weth.transfer(th.address, Wei("9 ether"), {"from": whale})

    w_weth_balance = planner.call(weth, "balanceOf", th.address)
    w_weth_balance = weiroll.ReturnValue("bytes32", w_weth_balance.command)
    swap_url = "https://api.1inch.io/v4.0/1/swap"
    print(th.address)
    r = requests.get(
        swap_url,
        params={
            "fromTokenAddress": weth.address,
            "toTokenAddress": crv.address,
            "amount": Wei("10 ether"),
            "fromAddress": th.address,
            "slippage": 5,
            "disableEstimate": "true",
            "allowPartialFill": "false",
            "usePatching": "true",
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]
    router = tx["to"]
    print(f"router: {router}")
    weth.approve(router, 0, {"from": th, "gas_price": 0})
    weth.approve(router, 2**256 - 1, {"from": th, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]
    params[1][5] = 1  # minReturn

    struct_layout = (
        "(address,address,address,address,uint256,uint256,uint256,bytes)"
    )
    tuple_bytes = eth_abi.encode_single(struct_layout, params[1])
    tuple_raw = planner.add(
        w_tuple_helper.replaceElement(
            tuple_bytes, 4, w_weth_balance, True
        ).rawValue()
    )

    tuple_raw = weiroll.ReturnValue(
        struct_layout, tuple_raw.command
    )
    params[1] = tuple_raw

    print(params)

    w_router = weiroll.WeirollContract.createContract(router_like)
    planner.call(router_like, "swapSimple", params[1])
    # planner.add(w_router.swap(params[0], params[1], params[2]))

    cmds, state = planner.plan()

    weiroll_tx = th.execute(
        cmds, state, {"from": ms, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(th) > 0
    print(crv.balanceOf(th))
    assert False

def test_tuple_replace():
    whale = accounts.at(
        "0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True
    )
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    tuple_helper = Contract("0x06706E366159cEfD3789184686da5cC3f47fB4a2")
    w_tuple_helper = weiroll.WeirollContract(tuple_helper)
    th = Contract("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b")
    ms = accounts.at("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6", force=True)
    planner = WeirollPlanner(th)

    weth_balance_whale = weth.balanceOf(whale)

    # transfer all of whale's weth to th
    weth.approve(th.address, 2**256 - 1, {"from": whale})
    weth.transfer(th.address, weth.balanceOf(whale), {"from": whale})

    # get weiroll amount
    w_weth_balance = planner.call(weth, "balanceOf", th.address)
    w_weth_balance = weiroll.ReturnValue("bytes32", w_weth_balance.command)

    tuple = [
        crv.address,
        crv.address,
        crv.address,
        crv.address,
        999,
        1,
        999,
        b"0x0",
    ]
    struct_layout = (
        "(address,address,address,address,uint256,uint256,uint256,bytes)"
    )
    tuple_bytes = eth_abi.encode_single(struct_layout, tuple)

    # replace amount with w_amount
    tuple_description_bytes = planner.add(
        w_tuple_helper.replaceElement(
            tuple_bytes, 4, w_weth_balance, True
        ).rawValue()
    )

    print(tuple_description_bytes)

    tuple_description = weiroll.ReturnValue(
        struct_layout, tuple_description_bytes.command
    )

    # do some transfers in order to verify amount was correctly replaced
    actual_balance = planner.add(
        w_tuple_helper.getElement(tuple_description_bytes, 4)
    )
    actual_minReturn = planner.add(
        w_tuple_helper.getElement(tuple_description_bytes, 5)
    )
    actual_balance = weiroll.ReturnValue("uint256", actual_balance.command)
    actual_minReturn = weiroll.ReturnValue("uint256", actual_minReturn.command)
    planner.call(weth, "transfer", ms.address, actual_balance)
    planner.call(crv, "approve", ms.address, actual_minReturn)

    cmds, state = planner.plan()

    weth_balance_ms = weth.balanceOf(ms)
    weiroll_tx = th.execute(
        cmds, state, {"from": ms, "gas_limit": 8_000_000, "gas_price": 0}
    )

    # assert replacing amount w/ w_amount worked
    assert weth.balanceOf(ms) - weth_balance_ms == weth_balance_whale
    assert crv.allowance(th, ms) == 1
