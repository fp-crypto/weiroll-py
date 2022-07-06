from brownie import TestableVM, interface, accounts, Contract, convert
from weiroll import WeirollContract, WeirollPlanner, hexConcat
from gnosis.safe import SafeOperation
from ape_safe import ApeSafe

safe = ApeSafe("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7")

def _tenderly_fork():
    import requests
    import brownie

    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": "1"}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = safe.w3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    safe.w3.provider = tenderly_provider
    brownie.web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


def weiroll_example():
    #_tenderly_fork()

    weth = safe.contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    crvseth = safe.contract("0xc5424B857f758E906013F3555Dad202e4bdB4567")
    susd = safe.contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51")

    weiroll_vm = accounts[0].deploy(TestableVM) 
    weiroll = WeirollContract
    planner = WeirollPlanner(safe)
    yvweth = weiroll.createContract(Contract("0x5120FeaBd5C21883a4696dBCC5D123d6270637E9"))
    weth = weiroll.createContract(Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"))
    susd = weiroll.createContract(Contract("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51"))
    seth = weiroll.createContract(Contract(crvseth.coins(1)))

    sushi_router_w = weiroll.createContract(Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"))
    univ3_router_w = weiroll.createContract(Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564"))

    planner.call(yvweth.brownieContract, "withdraw(uint256)", int(1e18))
    
    weth_bal = planner.add(weth.balanceOf(safe.address))

    planner.add(weth.approve(sushi_router_w.address, weth_bal))
    planner.add(sushi_router_w.swapExactTokensForTokens(
        weth_bal,
        0,
        [weth.address, susd.address],
        safe.address,
        2**256-1
    ))

    susd_bal = planner.add(susd.balanceOf(safe.address))
    planner.add(susd.approve(sushi_router_w.address, susd_bal))
    planner.add(sushi_router_w.swapExactTokensForTokens(
        susd_bal,
        0,
        [susd.address, weth.address, seth.address],
        safe.address,
        2**256-1
    ))

    seth_bal = planner.add(seth.balanceOf(safe.address))
    planner.add(seth.approve(univ3_router_w.address, seth_bal))
    planner.add(univ3_router_w.exactInputSingle(
        (
            seth.address,
            weth.address,
            500,
            safe.address,
            2**256-1,
            seth_bal,
            0,
            0
        )
    ))

    cmds, state = planner.plan()
    tx_input = weiroll_vm.execute.encode_input(cmds, state)

    safe_tx = safe.build_multisig_tx(weiroll_vm.address, 0, tx_input, SafeOperation.DELEGATE_CALL.value, safe.pending_nonce())
    safe.preview(safe_tx, reset=False, call_trace=True)
