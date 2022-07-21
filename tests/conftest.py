import pytest
from brownie import config, Contract, network
import requests
from weiroll import WeirollContract

# @pytest.fixture(scope="session", autouse=True)
# def _tenderly_fork():
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


@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[0]


@pytest.fixture(scope="module")
def weiroll_vm(alice, TestableVM):
    vm = alice.deploy(TestableVM)
    yield vm


@pytest.fixture(scope="module")
def math(alice, Math):
    math_brownie = alice.deploy(Math)
    yield WeirollContract.createLibrary(math_brownie)


@pytest.fixture(scope="module")
def testContract(alice, TestContract):
    brownie_contract = alice.deploy(TestContract)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="module")
def strings(alice, Strings):
    strings_brownie = alice.deploy(Strings)
    yield WeirollContract.createLibrary(strings_brownie)


@pytest.fixture(scope="module")
def subplanContract(alice, TestSubplan):
    brownie_contract = alice.deploy(TestSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="module")
def multiSubplanContract(alice, TestMultiSubplan):
    brownie_contract = alice.deploy(TestMultiSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="module")
def badSubplanContract(alice, TestBadSubplan):
    brownie_contract = alice.deploy(TestBadSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="module")
def multiStateSubplanContract(alice, TestMultiStateSubplan):
    brownie_contract = alice.deploy(TestMultiStateSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="module")
def readonlySubplanContract(alice, TestReadonlySubplan):
    brownie_contract = alice.deploy(TestReadonlySubplan)
    yield WeirollContract.createLibrary(brownie_contract)
