import weiroll
from weiroll import WeirollContract
from ape_safe import ApeSafe
from gnosis.safe import SafeOperation
from brownie import Contract
from math import isclose


def test_univ3_lp(alice, weiroll_vm, UniswapV3Helper):

    helper = WeirollContract.createContract(alice.deploy(UniswapV3Helper))

    safe = ApeSafe("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7")

    planner = weiroll.WeirollPlanner(safe)

    # Read providers
    provider_usdc = WeirollContract.createContract(
        Contract("0xD94f90E8df35c649573b6d2F909EDd8C8a791422")
    )
    provider_usdt = WeirollContract.createContract(
        Contract("0xdb67Dd2f3074bA25da2A487B1C61D3b3aF9aafA8")
    )

    joint = safe.contract(provider_usdc.brownieContract.joint())

    # Read vaults
    vault_usdc = WeirollContract.createContract(
        Contract(provider_usdc.brownieContract.vault())
    )
    vault_usdt = WeirollContract.createContract(
        Contract(provider_usdt.brownieContract.vault())
    )

    # Total between both amounts ahould be ~1m
    target_usdc = int(1_000_000 * 10 ** 6)
    dr_usdc = int(target_usdc / vault_usdc.brownieContract.totalAssets() * 1e4)

    # Total between both amounts ahould be ~1m
    target_usdt = int(1_000_000 * 10 ** 6)
    dr_usdt = int(target_usdt / vault_usdt.brownieContract.totalAssets() * 1e4)

    # Need to allocate some extra DR due to real debt ratios != desired debt ratios
    planner.add(
        vault_usdc.updateStrategyDebtRatio(provider_usdc.address, int(dr_usdc + 1500))
    )
    planner.add(
        vault_usdt.updateStrategyDebtRatio(provider_usdt.address, int(dr_usdt + 1000))
    )

    w_amount_usdc = planner.add(
        helper.getLPAmount0(joint.pool(), -4, -1, target_usdc, target_usdt)
    )
    w_amount_usdt = planner.add(
        helper.getLPAmount1(joint.pool(), -4, -1, target_usdc, target_usdt)
    )

    # Need to allocate some extra DR due to real debt ratios != desired debt ratios
    planner.add(
        vault_usdc.updateStrategyMaxDebtPerHarvest(provider_usdc.address, w_amount_usdc)
    )
    planner.add(
        vault_usdt.updateStrategyMaxDebtPerHarvest(provider_usdt.address, w_amount_usdt)
    )

    # Harvest providers to launch it
    planner.add(provider_usdc.harvest())
    planner.add(provider_usdt.harvest())

    # Give back dr usdc and usdt
    planner.add(vault_usdc.updateStrategyDebtRatio(provider_usdc.address, 0))
    planner.add(vault_usdt.updateStrategyDebtRatio(provider_usdt.address, 0))
    # Avoid getting new debt in harvest trigger
    planner.add(vault_usdc.updateStrategyMaxDebtPerHarvest(provider_usdc.address, 0))
    planner.add(vault_usdt.updateStrategyMaxDebtPerHarvest(provider_usdt.address, 0))

    cmds, state = planner.plan()
    tx_input = weiroll_vm.execute.encode_input(cmds, state)

    safe_tx = safe.build_multisig_tx(
        weiroll_vm.address,
        0,
        tx_input,
        SafeOperation.DELEGATE_CALL.value,
        safe.pending_nonce(),
    )
    safe.preview(safe_tx, reset=False, call_trace=True)

    assert isclose(joint.balanceOfTokensInLP()[0] / 1e6, target_usdc / 1e6) or isclose(
        joint.balanceOfTokensInLP()[1] / 1e6, target_usdt / 1e6
    )
    assert isclose(
        provider_usdc.brownieContract.balanceOfWant() / 1e6, 0, rel_tol=1e-3
    ) and isclose(provider_usdt.brownieContract.balanceOfWant() / 1e6, 0, rel_tol=1e-3)
