from brownie import Contract, accounts, Wei, chain, TestableVM
from weiroll import WeirollContract, WeirollPlanner, ReturnValue
import requests


def test_chaining_action(weiroll_vm, tuple_helper):
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    yfi = Contract("0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")

    # Check initial setup and send 10 eth to start the process
    assert weth.balanceOf(weiroll_vm.address) == 0
    assert yfi.balanceOf(weiroll_vm.address) == 0
    weth.transfer(weiroll_vm.address, Wei("10 ether"), {"from": whale})

    planner = WeirollPlanner(weiroll_vm)
    w_one_inch = WeirollContract.createContract(one_inch)
    w_weth = WeirollContract.createContract(weth)
    w_yfi = WeirollContract.createContract(yfi)
    w_tuple_helper = WeirollContract.createContract(tuple_helper)

    planner.add(w_weth.approve(one_inch.address, 2**256-1))

    swap_url = "https://api.1inch.io/v4.0/1/swap"
    r = requests.get(
        swap_url,
        params={
            "fromTokenAddress": weth.address,
            "toTokenAddress": yfi.address,
            "amount": Wei("10 ether"),
            "fromAddress": weiroll_vm.address,
            "slippage": 5,
            "disableEstimate": "true",
            "allowPartialFill": "false",
        },
    )

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    decoded = one_inch.decode_input(tx["data"])
    func_name = decoded[0]
    params = decoded[1]

    one_inch_ret = planner.add(
        w_one_inch.swap(*params).rawValue()
    )

    one_inch_amount = planner.add(w_tuple_helper.getElement(one_inch_ret, 0))
    int_amount = ReturnValue('uint256', one_inch_amount.command)

    planner.add(w_yfi.transfer(w_tuple_helper.address, int_amount))


    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    # This works fine
    assert yfi.balanceOf(tuple_helper) > 0
    assert False
