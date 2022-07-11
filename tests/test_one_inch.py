from brownie import Contract, accounts, Wei, chain, TestableVM
from weiroll import WeirollContract, WeirollPlanner
import requests

def test_one_inch():
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    one_inch = Contract("0x1111111254fb6c44bAC0beD2854e76F90643097d")

    vm = TestableVM.deploy({"from": whale})
    weth.transfer(vm.address, Wei("10 ether"), {"from": whale})
    #assert False
    swap_url = "https://api.1inch.io/v4.0/1/swap"
    r = requests.get(swap_url, params={
        "fromTokenAddress": weth.address,
        "toTokenAddress": crv.address,
        "amount": Wei("10 ether"),
        "fromAddress": vm.address,
        "slippage": 5,
        "disableEstimate": "true",
        "allowPartialFill": "false"
    })

    assert r.ok and r.status_code == 200
    tx = r.json()["tx"]

    # This approve is needed for both, regular and weiroll version
    weth.approve(one_inch, 2**256-1, {"from": vm, "gas_price": 0})

    decoded = one_inch.decode_input(tx['data'])
    func_name = decoded[0]
    params = decoded[1]

    # Weiroll version which reverts
    planner = WeirollPlanner(vm)
    planner.call(one_inch, func_name, *params)

    cmds, state = planner.plan()
    weiroll_tx = vm.execute(cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0})

    # This works fine
    assert crv.balanceOf(vm) > 0
