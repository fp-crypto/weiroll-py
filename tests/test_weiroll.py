import brownie
import eth_abi
import pytest
from hexbytes import HexBytes
import json

import weiroll

SAMPLE_ADDRESS = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee';

@pytest.fixture
def alice(accounts):
    return accounts[0]

#@pytest.fixture
#def subplanContract(alice):
#    brownie_contract = alice.deploy(brownie.WeirollTestSubplan)
#    return weiroll.WeirollContract.createLibrary(brownie_contract)
#
#
#@pytest.fixture
#def multiSubplanContract(alice):
#    brownie_contract = alice.deploy(brownie.WeirollTestMultiSubplan)
#    return weiroll.WeirollContract.createLibrary(brownie_contract)
#
#
#@pytest.fixture
#def multiStateSubplanContract(alice):
#    brownie_contract = alice.deploy(brownie.WeirollTestMultiStateSubplan)
#    return weiroll.WeirollContract.createLibrary(brownie_contract)
#
#
#@pytest.fixture
#def readonlySubplanContract(alice):
#    brownie_contract = alice.deploy(brownie.WeirollTestReadonlySubplan)
#    return weiroll.WeirollContract.createLibrary(brownie_contract)
#
#
#@pytest.fixture
#def testContract(alice):
#    brownie_contract = alice.deploy(brownie.WeirollTest)
#    return weiroll.WeirollContract.createLibrary(brownie_contract)


def test_weiroll_contract(math):
    assert hasattr(math, "add")

    result = math.add(1, 2)

    assert result.contract == math
    # assert result.fragment.function.signature == math.add.signature
    assert result.fragment.inputs == ["uint256", "uint256"]
    assert result.fragment.name == "add"
    assert result.fragment.outputs == ["uint256"]
    assert result.fragment.signature == "0x771602f7"
    assert result.callvalue == 0
    assert result.flags == weiroll.CommandFlags.DELEGATECALL

    args = result.args
    assert len(args) == 2
    assert args[0].param == "uint256"
    assert args[0].value == eth_abi.encode_single("uint256", 1)
    assert args[1].param == "uint256"
    assert args[1].value == eth_abi.encode_single("uint256", 2)


def test_weiroll_planner_adds(alice, math):
    planner = weiroll.WeirollPlanner(alice)
    sum1 = planner.add(math.add(1, 2))
    sum2 = planner.add(math.add(3, 4))
    planner.add(math.add(sum1, sum2))

    assert len(planner.commands) == 3


def test_weiroll_planner_simple_program(alice, math):
    planner = weiroll.WeirollPlanner(alice)
    planner.add(math.add(1, 2))

    commands, state = planner.plan()

    assert len(commands) == 1
    # TODO: hexconcat?
    assert commands[0] == weiroll.hexConcat("0x771602f7000001ffffffffff", math.address)

    assert len(state) == 2
    assert state[0] == eth_abi.encode_single("uint", 1)
    assert state[1] == eth_abi.encode_single("uint", 2)


def test_weiroll_deduplicates_identical_literals(alice, math):
    planner = weiroll.WeirollPlanner(alice)
    planner.add(math.add(1, 1))
    commands, state = planner.plan()
    assert len(commands) == 1
    assert len(state) == 1
    assert state[0] == eth_abi.encode_single("uint", 1)


def test_weiroll_with_return_value(alice, math):
    planner = weiroll.WeirollPlanner(alice)

    sum1 = planner.add(math.add(1, 2))
    planner.add(math.add(sum1, 3))
    commands, state = planner.plan()

    assert len(commands) == 2
    assert commands[0] == weiroll.hexConcat("0x771602f7000001ffffffff01", math.address)
    assert commands[1] == weiroll.hexConcat("0x771602f7000102ffffffffff", math.address)

    assert len(state) == 3
    assert state[0] == eth_abi.encode_single("uint", 1)
    assert state[1] == eth_abi.encode_single("uint", 2)
    assert state[2] == eth_abi.encode_single("uint", 3)


def test_weiroll_with_state_slots_for_intermediate_values(alice, math):
    planner = weiroll.WeirollPlanner(alice)
    sum1 = planner.add(math.add(1, 1))
    planner.add(math.add(1, sum1))

    commands, state = planner.plan()

    assert len(commands) == 2
    assert commands[0] == weiroll.hexConcat("0x771602f7000000ffffffff01", math.address)
    assert commands[1] == weiroll.hexConcat("0x771602f7000001ffffffffff", math.address)

    assert len(state) == 2
    assert state[0] == eth_abi.encode_single("uint", 1)
    assert state[1] == b""


@pytest.mark.parametrize(
    "param,value,expected",
    [
        (
            "string",
            "Hello, world!",
            "0x000000000000000000000000000000000000000000000000000000000000000d48656c6c6f2c20776f726c642100000000000000000000000000000000000000",
        ),
    ],
)
def test_weiroll_abi_encode_single(param, value, expected):
    expected = HexBytes(expected)
    print("expected:", expected)

    literalValue = HexBytes(eth_abi.encode_single(param, value))
    print("literalValue:", literalValue)

    assert literalValue == expected


def test_weiroll_takes_dynamic_arguments(alice, strings):
    test_str = "Hello, world!"

    planner = weiroll.WeirollPlanner(alice)
    planner.add(strings.strlen(test_str))
    commands, state = planner.plan()

    assert len(commands) == 1
    assert commands[0] == weiroll.hexConcat("0x367bbd780080ffffffffffff", strings.address)

    print(state)
    assert len(state) == 1
    assert state[0] == eth_abi.encode_single("string", test_str)


def test_weiroll_returns_dynamic_arguments(alice, strings):
    planner = weiroll.WeirollPlanner(alice)
    planner.add(strings.strcat("Hello, ", "world!"))
    commands, state = planner.plan()

    assert len(commands) == 1
    assert commands[0] == weiroll.hexConcat("0xd824ccf3008081ffffffffff", strings.address)

    assert len(state) == 2
    assert state[0] == eth_abi.encode_single("string", "Hello, ")
    assert state[1] == eth_abi.encode_single("string", "world!")


def test_weiroll_takes_dynamic_argument_from_a_return_value(alice, strings):
    planner = weiroll.WeirollPlanner(alice)
    test_str = planner.add(strings.strcat("Hello, ", "world!"))
    planner.add(strings.strlen(test_str))
    commands, state = planner.plan()

    assert len(commands) == 2
    assert commands[0] == weiroll.hexConcat("0xd824ccf3008081ffffffff81", strings.address)
    assert commands[1] == weiroll.hexConcat("0x367bbd780081ffffffffffff", strings.address)

    assert len(state) == 2
    assert state[0] == eth_abi.encode_single("string", "Hello, ")
    assert state[1] == eth_abi.encode_single("string", "world!")


def test_weiroll_argument_counts_match(math):
    with pytest.raises(ValueError):
        math.add(1)


# def test_weiroll_func_takes_and_replaces_current_state(alice, testContract):
#     planner = weiroll.WeirollPlanner(alice)
# 
#     planner.replaceState(testContract.useState(planner.state))
# 
#     commands, state = planner.plan()
# 
#     assert len(commands) == 1
#     assert commands[0] == weiroll.hexConcat("0x08f389c800fefffffffffffe", testContract.address)
# 
#     assert len(state) == 0
# 
# 
# def test_weiroll_supports_subplan(alice, math, subplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(subplanContract.execute(subplanner, subplanner.state))
# 
#     commands, state = planner.plan()
#     assert commands == [weiroll.hexConcat("0xde792d5f0082fefffffffffe", subplanContract.address)]
# 
#     assert len(state) == 3
#     assert state[0] == eth_abi.encode_single("uint", 1)
#     assert state[1] == eth_abi.encode_single("uint", 2)
#     # TODO: javascript test is more complicated than this. but i think this is fine?
#     assert state[2] == weiroll.hexConcat("0x771602f7000001ffffffffff", math.address)
# 
# 
# def test_weiroll_subplan_allows_return_in_parent_scope(alice, math, subplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     sum = subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(subplanContract.execute(subplanner, subplanner.state))
#     planner.add(math.add(sum, 3))
# 
#     commands, _ = planner.plan()
#     assert len(commands) == 2
#     # Invoke subplanner
#     assert commands[0] == weiroll.hexConcat("0xde792d5f0083fefffffffffe", subplanContract.address)
#     # sum + 3
#     assert commands[1] == weiroll.hexConcat("0x771602f7000102ffffffffff", math.address)
# 
# 
# def test_weiroll_return_values_across_scopes(alice, math, subplanContract):
#     subplanner1 = weiroll.WeirollPlanner(alice)
#     sum = subplanner1.add(math.add(1, 2))
# 
#     subplanner2 = weiroll.WeirollPlanner(alice)
#     subplanner2.add(math.add(sum, 3))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(subplanContract.execute(subplanner1, subplanner1.state))
#     planner.addSubplan(subplanContract.execute(subplanner2, subplanner2.state))
# 
#     commands, state = planner.plan()
# 
#     assert len(commands) == 2
#     assert commands[0] == weiroll.hexConcat("0xde792d5f0083fefffffffffe", subplanContract.address)
#     assert commands[1] == weiroll.hexConcat("0xde792d5f0084fefffffffffe", subplanContract.address)
# 
#     assert len(state) == 5
#     # TODO: javascript tests were more complex than this
#     assert state[4] == weiroll.hexConcat("0x771602f7000102ffffffffff", math.address)


def test_weiroll_return_values_must_be_defined(alice, math):
    subplanner = weiroll.WeirollPlanner(alice)
    sum = subplanner.add(math.add(1, 2))

    planner = weiroll.WeirollPlanner(alice)
    planner.add(math.add(sum, 3))

    with pytest.raises(ValueError, match="Return value from 'add' is not visible here"):
        planner.plan()


# def test_weiroll_add_subplan_needs_args(alice, math, subplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
# 
#     with pytest.raises(ValueError, match="Subplans must take planner and state arguments"):
#         planner.addSubplan(subplanContract.execute(subplanner, []))
# 
#     with pytest.raises(ValueError, match="Subplans must take planner and state arguments"):
#         planner.addSubplan(subplanContract.execute([], subplanner.state))
# 
# 
# def test_weiroll_doesnt_allow_multiple_subplans_per_call(alice, math, multiSubplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     with pytest.raises(ValueError, match="Subplans can only take one planner argument"):
#         planner.addSubplan(multiSubplanContract.execute(subplanner, subplanner, subplanner.state))
# 
# 
# def test_weiroll_doesnt_allow_state_array_per_call(alice, math, multiStateSubplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     with pytest.raises(ValueError, match="Subplans can only take one state argument"):
#         planner.addSubplan(multiStateSubplanContract.execute(subplanner, subplanner.state, subplanner.state))
# 
# 
# def test_weiroll_subplan_has_correct_return_type(alice, math):
#     badSubplanContract = weiroll.WeirollContract.createLibrary(alice.deploy(brownie.WeirollBadSubplan))
# 
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     with pytest.raises(ValueError, match=r"Subplans must return a bytes\[\] replacement state or nothing"):
#         planner.addSubplan(badSubplanContract.execute(subplanner, subplanner.state))
# 
# 
# def test_forbid_infinite_loops(alice, subplanContract):
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(subplanContract.execute(planner, planner.state))
# 
#     with pytest.raises(ValueError, match="A planner cannot contain itself"):
#         planner.plan()
# 
# 
# def test_subplans_without_returns(alice, math, readonlySubplanContract):
#     subplanner = weiroll.WeirollPlanner(alice)
#     subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(readonlySubplanContract.execute(subplanner, subplanner.state))
# 
#     commands, _ = planner.plan()
# 
#     assert len(commands) == 1
#     commands[0] == weiroll.hexConcat("0xde792d5f0082feffffffffff", readonlySubplanContract.address)
# 
# 
# def test_read_only_subplans_requirements(alice, math, readonlySubplanContract):
#     """it does not allow return values from inside read-only subplans to be used outside them"""
#     subplanner = weiroll.WeirollPlanner(alice)
#     sum = subplanner.add(math.add(1, 2))
# 
#     planner = weiroll.WeirollPlanner(alice)
#     planner.addSubplan(readonlySubplanContract.execute(subplanner, subplanner.state))
#     planner.add(math.add(sum, 3))
# 
#     with pytest.raises(ValueError, match="Return value from 'add' is not visible here"):
#         planner.plan()


@pytest.mark.xfail(reason="need to write this")
def test_plan_with_loop(alice):
    target_calldata = "0xc6b6816900000000000000000000000000000000000000000000054b40b1f852bda0"

    """
    [
    '0x0000000000000000000000000000000000000000000000000000000000000005',
    '0x000000000000000000000000cecad69d7d4ed6d52efcfa028af8732f27e08f70',
    '0x0000000000000000000000000000000000000000000000000000000000000022c6b6816900000000000000000000000000000000000000000000054b40b1f852bda0000000000000000000000000000000000000000000000000000000000000'
    ]
    """
    planner = weiroll.WeirollPlanner(alice)

    raise NotImplementedError


def _test_more(math):

    # TODO: test for curve add_liquidity encoding
    """

        expect(() => planner.plan()).to.throw(
            'Return value from "add" is not visible here'
        );
    });

    it('plans CALLs', () => {
        let Math = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, mathABI.abi)
        );

        const planner = new Planner();
        planner.add(Math.add(1, 2));
        const { commands } = planner.plan();

        expect(commands.length).to.equal(1);
        expect(commands[0]).to.equal(
        '0x771602f7010001ffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        );
    });

    it('plans STATICCALLs', () => {
        let Math = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, mathABI.abi),
        CommandFlags.STATICCALL
        );

        const planner = new Planner();
        planner.add(Math.add(1, 2));
        const { commands } = planner.plan();

        expect(commands.length).to.equal(1);
        expect(commands[0]).to.equal(
        '0x771602f7020001ffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        );
    });

    it('plans STATICCALLs via .staticcall()', () => {
        let Math = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, mathABI.abi)
        );

        const planner = new Planner();
        planner.add(Math.add(1, 2).staticcall());
        const { commands } = planner.plan();

        expect(commands.length).to.equal(1);
        expect(commands[0]).to.equal(
        '0x771602f7020001ffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        );
    });

    it('plans CALLs with value', () => {
        const Test = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, ['function deposit(uint x) payable'])
        );

        const planner = new Planner();
        planner.add(Test.deposit(123).withValue(456));

        const { commands } = planner.plan();
        expect(commands.length).to.equal(1);
        expect(commands[0]).to.equal(
        '0xb6b55f25030001ffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        );
    });

    it('allows returns from other calls to be used for the value parameter', () => {
        const Test = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, ['function deposit(uint x) payable'])
        );

        const planner = new Planner();
        const sum = planner.add(Math.add(1, 2));
        planner.add(Test.deposit(123).withValue(sum));

        const { commands } = planner.plan();
        expect(commands.length).to.equal(2);
        expect(commands).to.deep.equal([
        '0x771602f7000001ffffffff01eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        '0xb6b55f25030102ffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        ]);
    });

    it('does not allow value-calls for DELEGATECALL or STATICCALL', () => {
        expect(() => Math.add(1, 2).withValue(3)).to.throw(
        'Only CALL operations can send value'
        );

        const StaticMath = Contract.createContract(
        new ethers.Contract(SAMPLE_ADDRESS, mathABI.abi),
        CommandFlags.STATICCALL
        );
        expect(() => StaticMath.add(1, 2).withValue(3)).to.throw(
        'Only CALL operations can send value'
        );
    });

    it('does not allow making DELEGATECALL static', () => {
        expect(() => Math.add(1, 2).staticcall()).to.throw(
        'Only CALL operations can be made static'
        );
    });

    it('uses extended commands where necessary', () => {
        const Test = Contract.createLibrary(
        new ethers.Contract(SAMPLE_ADDRESS, [
            'function test(uint a, uint b, uint c, uint d, uint e, uint f, uint g) returns(uint)',
        ])
        );

        const planner = new Planner();
        planner.add(Test.test(1, 2, 3, 4, 5, 6, 7));
        const { commands } = planner.plan();
        expect(commands.length).to.equal(2);
        expect(commands[0]).to.equal(
        '0xe473580d40000000000000ffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
        );
        expect(commands[1]).to.equal(
        '0x00010203040506ffffffffffffffffffffffffffffffffffffffffffffffffff'
        );
    });

    it('supports capturing the whole return value as a bytes', () => {
        const Test = Contract.createLibrary(
        new ethers.Contract(SAMPLE_ADDRESS, [
            'function returnsTuple() returns(uint a, bytes32[] b)',
            'function acceptsBytes(bytes raw)',
        ])
        );

        const planner = new Planner();
        const ret = planner.add(Test.returnsTuple().rawValue());
        planner.add(Test.acceptsBytes(ret));
        const { commands } = planner.plan();
        expect(commands).to.deep.equal([
        '0x61a7e05e80ffffffffffff80eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        '0x3e9ef66a0080ffffffffffffeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        ]);
    });
    """
