from brownie import TestableVM, Contract, convert
from weiroll import WeirollContract, WeirollPlanner
import weiroll
from web3 import Web3
import random
import eth_abi
import pytest


def test_swaps(accounts, weiroll_vm):
    whale = accounts.at("0xF5BCE5077908a1b7370B9ae04AdC565EBd643966", force=True)

    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crvseth = Contract("0xc5424B857f758E906013F3555Dad202e4bdB4567")
    susd = Contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51")

    weiroll_vm = accounts[0].deploy(TestableVM)
    planner = WeirollPlanner(whale)
    yvweth = WeirollContract.createContract(
        Contract("0xa258C4606Ca8206D8aA700cE2143D7db854D168c")
    )
    weth = WeirollContract.createContract(
        Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    )
    susd = WeirollContract.createContract(
        Contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51")
    )
    seth = WeirollContract.createContract(Contract(crvseth.coins(1)))

    sushi_router_w = WeirollContract.createContract(
        Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    )
    univ3_router_w = WeirollContract.createContract(
        Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    )

    yvweth.brownieContract.transfer(weiroll_vm, 2e18, {"from": whale})
    weth.brownieContract.transfer(weiroll_vm, 1.118383e18, {"from": whale})

    planner.call(yvweth.brownieContract, "withdraw(uint256)", int(1e18))

    weth_bal = planner.add(weth.balanceOf(weiroll_vm.address))

    planner.add(weth.approve(sushi_router_w.address, weth_bal))
    planner.add(
        sushi_router_w.swapExactTokensForTokens(
            weth_bal, 0, [weth.address, susd.address], weiroll_vm.address, 2 ** 256 - 1
        )
    )

    susd_bal = planner.add(susd.balanceOf(weiroll_vm.address))
    planner.add(susd.approve(sushi_router_w.address, susd_bal))
    planner.add(
        sushi_router_w.swapExactTokensForTokens(
            susd_bal,
            0,
            [susd.address, weth.address, seth.address],
            weiroll_vm.address,
            2 ** 256 - 1,
        )
    )

    seth_bal = planner.add(seth.balanceOf(weiroll_vm.address))
    planner.add(seth.approve(univ3_router_w.address, seth_bal))
    planner.add(
        univ3_router_w.exactInputSingle(
            (
                seth.address,
                weth.address,
                500,
                weiroll_vm.address,
                2 ** 256 - 1,
                seth_bal,
                0,
                0,
            )
        )
    )

    cmds, state = planner.plan()
    weiroll_tx = weiroll_vm.execute(
        cmds, state, {"from": weiroll_vm, "gas_limit": 8_000_000, "gas_price": 0}
    )


def test_balancer_swap(accounts, weiroll_vm, tuple_helper):

    bal_whale = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    bal_amount = random.randint(1000, 50000) * 10 ** 18

    planner = WeirollPlanner(weiroll_vm)

    bal = Contract("0xba100000625a3754423978a60c9317c58a424e3D")
    weth = Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    balancer_vault = Contract("0xBA12222222228d8Ba445958a75a0704d566BF2C8")

    bal.transfer(weiroll_vm, bal_amount, {"from": bal_whale})

    w_bal = WeirollContract.createContract(bal)
    w_balancer_vault = WeirollContract.createContract(balancer_vault)
    w_tuple_helper = WeirollContract(tuple_helper)

    w_bal_balance = planner.add(w_bal.balanceOf(weiroll_vm.address))

    planner.add(w_bal.approve(w_balancer_vault.address, w_bal_balance))

    bal_weth_pool_id = convert.to_bytes(
        "0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014", "bytes32"
    )
    deadline = int(999999999999999999)

    min_out_weth_bal = int(bal_amount * 0.001)

    fund_settings = {
        "sender": weiroll_vm.address,
        "recipient": weiroll_vm.address,
        "fromInternalBalance": False,
        "toInternalBalance": False,
    }

    swap = {
        "poolId": bal_weth_pool_id,
        "assetIn": bal.address,
        "assetOut": weth.address,
        "amount": w_bal_balance,
    }
    swap_kind = int(0)  # GIVEN_IN

    user_data = convert.to_bytes(bal_weth_pool_id, "bytes")

    swap_struct = (
        swap["poolId"],
        swap_kind,
        Web3.toChecksumAddress(swap["assetIn"]),
        Web3.toChecksumAddress(swap["assetOut"]),
        0,  # replace with w_bal_balance,
        user_data,
    )

    w_bal_balance = weiroll.ReturnValue("bytes32", w_bal_balance.command)
    swap_struct_layout = "(bytes32,uint8,address,address,uint256,bytes)"

    w_swap_struct = planner.add(
        w_tuple_helper.replaceElement(
            eth_abi.encode_single(swap_struct_layout, swap_struct),
            4,
            w_bal_balance,
            True,
        ).rawValue()
    )
    w_swap_struct = weiroll.ReturnValue(swap_struct_layout, w_swap_struct.command)

    fund_struct = (
        Web3.toChecksumAddress(fund_settings["sender"]),
        fund_settings["fromInternalBalance"],
        Web3.toChecksumAddress(fund_settings["recipient"]),
        fund_settings["toInternalBalance"],
    )

    planner.add(
        w_balancer_vault.swap(w_swap_struct, fund_struct, min_out_weth_bal, deadline)
    )

    cmds, state = planner.plan()
    
    assert bal.balanceOf(weiroll_vm) > 0
    assert weth.balanceOf(weiroll_vm) == 0

    weiroll_tx = weiroll_vm.execute(cmds, state)
    weiroll_tx.call_trace(True)

    assert bal.balanceOf(weiroll_vm) == 0
    assert weth.balanceOf(weiroll_vm) > min_out_weth_bal
