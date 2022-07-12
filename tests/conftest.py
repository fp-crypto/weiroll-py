import pytest
from brownie import config, Contract, network
import requests
from weiroll import WeirollContract

#@pytest.fixture(scope="session", autouse=True)
#def _tenderly_fork():
#    import requests
#    import brownie
#
#    fork_base_url = "https://simulate.yearn.network/fork"
#    payload = {"network_id": "1"}
#    resp = requests.post(fork_base_url, headers={}, json=payload)
#    fork_id = resp.json()["simulation_fork"]["id"]
#    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
#    print(fork_rpc_url)
#    tenderly_provider = safe.w3.HTTPProvider(fork_rpc_url, {"timeout": 600})
#    safe.w3.provider = tenderly_provider
#    brownie.web3.provider = tenderly_provider
#    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def weiroll_vm(accounts, TestableVM):
    vm = accounts[0].deploy(TestableVM)
    yield vm


@pytest.fixture(scope="module")
def math(accounts, Math):
    math_bronwie = accounts[0].deploy(Math)
    yield WeirollContract.createLibrary(math_bronwie)


@pytest.fixture(scope="module")
def strings(accounts, Strings):
    strings_brownie = accounts[0].deploy(Strings)
    yield WeirollContract.createLibrary(strings_brownie)
