from brownie import Contract, accounts, Wei, chain, TestableVM
from weiroll import WeirollContract, WeirollPlanner
import pytest


@pytest.mark.skip()
def test_vm_with_math(weiroll_vm_with_math):
    weiroll_vm = weiroll_vm_with_math
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)

    planner = WeirollPlanner(weiroll_vm)
    w_math = WeirollContract.createContract(weiroll_vm)
    sum = planner.add(w_math.sum(1, 2))
    sum_2 = planner.add(w_math.sum(3, sum))
    sum_3 = planner.add(w_math.sum3(3, sum_2, 4))
    planner.add(w_math.sub(sum_3, 3))

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )


# @pytest.mark.skip()
def test_vm_with_math_local_dispatch(weiroll_vm_with_math):
    weiroll_vm = weiroll_vm_with_math
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)

    planner = WeirollPlanner(weiroll_vm)
    w_math = WeirollContract.createContract(weiroll_vm)
    sum = planner.add(w_math.sum(1, 2).localDispatch())
    sum_2 = planner.add(w_math.sum(3, sum).localDispatch())
    sum_3 = planner.add(w_math.sum3(3, sum_2, 4).localDispatch())
    planner.add(w_math.sub(sum_3, 3).localDispatch())

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )


# @pytest.mark.skip()
def test_vm_with_math_auto_local_dispatch(weiroll_vm_with_math):
    weiroll_vm = weiroll_vm_with_math
    whale = accounts.at("0x57757E3D981446D585Af0D9Ae4d7DF6D64647806", force=True)

    planner = WeirollPlanner(weiroll_vm, auto_local_dispatch=True)
    w_math = WeirollContract.createContract(weiroll_vm)
    sum = planner.add(w_math.sum(1, 2))
    sum_2 = planner.add(w_math.sum(3, sum))
    sum_3 = planner.add(w_math.sum3(3, sum_2, 4))
    planner.add(w_math.sub(sum_3, 3))

    for command in planner.commands:
        assert(command.call.flags >> 5 & 0x1)

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": whale, "gas_limit": 8_000_000, "gas_price": 0}
    )
