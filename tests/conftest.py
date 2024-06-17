import pytest
from weiroll import WeirollContract


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def weiroll_vm(alice, TestableVM):
    vm = alice.deploy(TestableVM)
    yield vm


@pytest.fixture(scope="session")
def math(alice, Math):
    math_brownie = alice.deploy(Math)
    yield WeirollContract.createLibrary(math_brownie)


@pytest.fixture(scope="session")
def testContract(alice, TestContract):
    brownie_contract = alice.deploy(TestContract)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def strings(alice, Strings):
    strings_brownie = alice.deploy(Strings)
    yield WeirollContract.createLibrary(strings_brownie)


@pytest.fixture(scope="session")
def subplanContract(alice, TestSubplan):
    brownie_contract = alice.deploy(TestSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def multiSubplanContract(alice, TestMultiSubplan):
    brownie_contract = alice.deploy(TestMultiSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def badSubplanContract(alice, TestBadSubplan):
    brownie_contract = alice.deploy(TestBadSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def multiStateSubplanContract(alice, TestMultiStateSubplan):
    brownie_contract = alice.deploy(TestMultiStateSubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def readonlySubplanContract(alice, TestReadonlySubplan):
    brownie_contract = alice.deploy(TestReadonlySubplan)
    yield WeirollContract.createLibrary(brownie_contract)


@pytest.fixture(scope="session")
def tuple_helper(alice, TupleHelper):
    yield alice.deploy(TupleHelper)


@pytest.fixture(scope="session")
def tuple_helper_yul(alice, TupleHelperYul):
    yield alice.deploy(TupleHelperYul)


@pytest.fixture(scope="session")
def tuple_helper_vy(alice, TupleHelperVy):
    yield alice.deploy(TupleHelperVy)
