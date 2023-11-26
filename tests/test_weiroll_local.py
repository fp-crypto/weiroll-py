from brownie import Contract, accounts, Wei, chain, TestableVM
from weiroll import WeirollContract, WeirollPlanner


def test_vm_with_math(weiroll_vm_with_math):
    weiroll_vm = weiroll_vm_with_math
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)

    planner = WeirollPlanner(weiroll_vm)
    sum = planner.call(weiroll_vm, "sum", 1, 2)
    sum_2 = planner.call(weiroll_vm, "sum", sum, 3)
    sum_2 = planner.call(weiroll_vm, "sum", 3, sum_2)

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )

    print(weiroll_tx.return_value)
    #assert False
