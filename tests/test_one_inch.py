from brownie import Contract, accounts, Wei, chain, TestableVM, convert
from brownie.convert.datatypes import HexString

import weiroll
from weiroll import WeirollContract, WeirollPlanner, ReturnValue
import requests


def test_one_inch(weiroll_vm):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
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

    weth.approve(one_inch, 2 ** 256 - 1, {"from": weiroll_vm, "gas_price": 0})

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


def test_one_inch_replace_calldata_amount(weiroll_vm):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
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

    weth.approve(one_inch, 2 ** 256 - 1, {"from": weiroll_vm, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]
    calldata = params[2]

    # change inputs
    wei9 = Wei("9 ether")
    params[1][4] = wei9
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


def test_one_inch_replace_calldata_amount_2(weiroll_vm):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
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

    weth.approve(one_inch, 2 ** 256 - 1, {"from": weiroll_vm, "gas_price": 0})

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

def test_one_inch_replace_calldata_with_weiroll(weiroll_vm, tuple_helper):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")
    tuple_helper = Contract("0x06706E366159cEfD3789184686da5cC3f47fB4a2")
    w_tuple_helper = weiroll.WeirollContract(tuple_helper)
    th = accounts.at("0xcADBA199F3AC26F67f660C89d43eB1820b7f7a3b", force=True)
    planner = WeirollPlanner(th)

    weth.approve(th.address, Wei("10 ether"), {"from": whale})
    weth.transfer(th.address, Wei("10 ether"), {"from": whale})
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
            "usePatching": "true"
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    weth.approve(one_inch, 2 ** 256 - 1, {"from": th, "gas_price": 0})

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]
    print(func_name)

    struct_layout = '(address,address,address,address,uint256,uint256,uint256,bytes)'
    tuple_bytes = eth_abi.encode_single(struct_layout, params[1])
    min_return = eth_abi.encode_single("uint256", 1)
    tuple_description = planner.add(w_tuple_helper.replaceElement(tuple_bytes, 4, w_weth_balance, True).rawValue())
    tuple_description = planner.add(w_tuple_helper.replaceElement(tuple_description, 5, min_return, True).rawValue())
    tuple_description = weiroll.ReturnValue(struct_layout, tuple_description.command)

    w_one_inch = weiroll.WeirollContract(one_inch)
    params[1] = tuple_description
    print(params)
    planner.add(w_one_inch.swap(params[0], tuple_description, params[2]).rawValue())

    cmds, state = planner.plan()
    weiroll_tx = th.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(th) > 0
    print(crv.balanceOf(th))
