from brownie import TestableVM, Contract
from weiroll import WeirollContract, WeirollPlanner


def test_swaps(accounts, weiroll_vm):
    whale = accounts.at("0xF5BCE5077908a1b7370B9ae04AdC565EBd643966", force=True)

    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crvseth = Contract("0xc5424B857f758E906013F3555Dad202e4bdB4567")
    susd = Contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51")

    weiroll_vm = accounts[0].deploy(TestableVM) 
    planner = WeirollPlanner(whale)
    yvweth = WeirollContract.createContract(Contract("0xa258C4606Ca8206D8aA700cE2143D7db854D168c"))
    weth = WeirollContract.createContract(Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"))
    susd = WeirollContract.createContract(Contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51"))
    seth = WeirollContract.createContract(Contract(crvseth.coins(1)))

    sushi_router_w = WeirollContract.createContract(Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"))
    univ3_router_w = WeirollContract.createContract(Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564"))

    yvweth.brownieContract.transfer(weiroll_vm, 2e18, {'from': whale})
    weth.brownieContract.transfer(weiroll_vm, 1.118383e18, {'from': whale})

    planner.call(yvweth.brownieContract, "withdraw(uint256)", int(1e18))
    
    weth_bal = planner.add(weth.balanceOf(weiroll_vm.address))

    planner.add(weth.approve(sushi_router_w.address, weth_bal))
    planner.add(sushi_router_w.swapExactTokensForTokens(
        weth_bal,
        0,
        [weth.address, susd.address],
        weiroll_vm.address,
        2**256-1
    ))

    susd_bal = planner.add(susd.balanceOf(weiroll_vm.address))
    planner.add(susd.approve(sushi_router_w.address, susd_bal))
    planner.add(sushi_router_w.swapExactTokensForTokens(
        susd_bal,
        0,
        [susd.address, weth.address, seth.address],
        weiroll_vm.address,
        2**256-1
    ))

    seth_bal = planner.add(seth.balanceOf(weiroll_vm.address))
    planner.add(seth.approve(univ3_router_w.address, seth_bal))
    planner.add(univ3_router_w.exactInputSingle(
        (
            seth.address,
            weth.address,
            500,
            weiroll_vm.address,
            2**256-1,
            seth_bal,
            0,
            0
        )
    ))

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(cmds, state, {"from": weiroll_vm, "gas_limit": 8_000_000, "gas_price": 0})
    print(weiroll_tx)
