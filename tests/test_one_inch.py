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
def test_one_inch_replace_calldata_with_weiroll(weiroll_vm, tuple_helper):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")
    w_tuple_helper = WeirollContract.createContract(tuple_helper)

    planner = WeirollPlanner(weiroll_vm)

    weth.transfer(weiroll_vm.address, Wei("10 ether"), {"from": whale})
    w_weth_balance = planner.call(weth, "balanceOf", weiroll_vm.address)
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
    # amount_in
    params[1][4] = w_weth_balance
    # minOut
    params[1][5] = 1

    # TODO: I believe calldata can also be weirolled like this (?)
    # calldata = params[3]
    # # to string
    # calldata_str = calldata.hex()
    # hex10 = HexString(hex(Wei("10 ether")), "bytes32").hex()
    #
    # indices = [m.start() for m in re.finditer(hex10, calldata_str)]
    # for i in indices: 
    # w_calldata = planner.add(w_tuple_helper.replaceElement(calldata, i, w_weth_balance,Fales))
    # params[2] = w_calldata

    w_one_inch = weiroll.WeirollContract(one_inch)
    planner.add(w_one_inch.swap(params[0], params[1], params[2]))
    # TODO: not sure why the w_weth_balance part isn't working
    # TODO: EncodingTypeError: Value `ReturnValue(param...` of type <class 'weiroll.ReturnValue'> cannot be encoded by UnsignedIntegerEncoder


    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    assert crv.balanceOf(weiroll_vm) > 0
    print(crv.balanceOf(weiroll_vm))
