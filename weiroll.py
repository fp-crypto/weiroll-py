import re
from collections import defaultdict, namedtuple
from enum import IntEnum, IntFlag
from functools import cache
from typing import Optional

import brownie
import eth_abi
import eth_abi.packed
from brownie.convert.utils import get_type_strings
from brownie.network.contract import OverloadedMethod
from hexbytes import HexBytes

MAX_UINT256 = 2**256-1

# TODO: real types?
Value = namedtuple("Value", "param")
LiteralValue = namedtuple("LiteralValue", "param,value")
ReturnValue = namedtuple("ReturnValue", "param,command")


def simple_type_strings(inputs) -> tuple[Optional[list[str]], Optional[list[int]]]:
    """cut state variables that are too long into 32 byte chunks.

    related: https://github.com/weiroll/weiroll.js/pull/34
    """


    if not inputs:
        return None, None

    simple_inputs = []
    simple_sizes = []
    for i in inputs:
        if i.endswith("]") and not i.endswith("[]"):
            # fixed size array. cut it up
            m = re.match(r"([a-z0-9]+)\[([0-9]+)\]", i)

            size = int(m.group(2))

            simple_inputs.extend([m.group(1)] * size)
            simple_sizes.append(size)
        elif i.startswith("(") and i.endswith(")") and not isDynamicType(i):
            types = i[1:-1].split(",")

            simple_inputs.extend(types)
            simple_sizes.append(len(types))
        else:
            simple_inputs.append(i)
            simple_sizes.append(1)

    if all([s == 1 for s in simple_sizes]):
        # if no inputs or all the inputs are easily handled sizes, we don't need to simplify them
        # we don't clear simple_inputs because its simpler for that to just be a copy of self.inputs
        simple_sizes = None

    return simple_inputs, simple_sizes


def simple_args(simple_sizes, args):
    """split up complex types into 32 byte chunks that weiroll state can handle."""
    if not simple_sizes:
        # no need to handle anything specially
        return args

    simplified = []
    for i, size in enumerate(simple_sizes):
        if size == 1:
            # no need to do anything fancy
            simplified.append(args[i])
        else:
            simplified.extend(args[i])

    return simplified


# TODO: not sure about this class. its mostly here because this is how the javascript sdk works. now that this works, i think we can start refactoring to use brownie more directly
class FunctionFragment:
    def __init__(self, brownieContract: brownie.Contract, selector):
        function_name = brownieContract.selectors[selector]

        function = getattr(brownieContract, function_name)

        if isinstance(function, OverloadedMethod):
            overloaded_func = None
            for m in function.methods.values():
                # TODO: everyone is inconsistent about signature vs selector vs name
                if m.signature == selector:
                    overloaded_func = m
                    break

            assert overloaded_func
            function = overloaded_func

        self.function = function
        self.name = function_name
        self.signature = function.signature
        self.inputs = get_type_strings(function.abi["inputs"])

        # look at the inputs that aren't dynamic types but also aren't 32 bytes long and cut them up
        self.simple_inputs, self.simple_sizes = simple_type_strings(self.inputs)

        self.outputs = get_type_strings(function.abi["outputs"])
        # TODO: do something to handle outputs of uncommon types?

    def encode_args(self, *args):
        if len(args) != len(self.inputs):
            raise ValueError(f"Function {self.name} has {len(self.inputs)} arguments but {len(self.args)} provided")

        # split up complex types into 32 byte chunks that weiroll state can handle
        args = simple_args(self.simple_sizes, args)

        return [encodeArg(arg, self.simple_inputs[i]) for (i, arg) in enumerate(args)]


class StateValue:
    def __init__(self):
        self.param = "bytes[]"


class SubplanValue:
    def __init__(self, planner):
        self.param = "bytes[]"
        self.planner = planner


# TODO: use python ABC or something like that?
def isValue(arg):
    if isinstance(arg, Value):
        return True
    if isinstance(arg, LiteralValue):
        return True
    if isinstance(arg, ReturnValue):
        return True
    if isinstance(arg, StateValue):
        return True
    if isinstance(arg, SubplanValue):
        return True
    return False


# TODO: this needs tests! I'm 90% sure this is wrong for lists
# TODO: does eth_utils not already have this? it seems like other people should have written something like this
def hexConcat(*items) -> HexBytes:
    result = b""
    for item in items:
        if isinstance(item, list):
            item = hexConcat(*item)
        else:
            item = HexBytes(item)
        result += bytes(item)
    return HexBytes(result)


class CommandFlags(IntFlag):
    # Specifies that a call should be made using the DELEGATECALL opcode
    DELEGATECALL = 0x00
    # Specifies that a call should be made using the CALL opcode
    CALL = 0x01
    # Specifies that a call should be made using the STATICCALL opcode
    STATICCALL = 0x02
    # Specifies that a call should be made using the CALL opcode, and that the first argument will be the value to send
    CALL_WITH_VALUE = 0x03
    # A bitmask that selects calltype flags
    CALLTYPE_MASK = 0x03
    # Specifies that this is an extended command, with an additional command word for indices. Internal use only.
    EXTENDED_COMMAND = 0x40
    # Specifies that the return value of this call should be wrapped in a `bytes`. Internal use only.
    TUPLE_RETURN = 0x80


class FunctionCall:
    def __init__(self, contract, flags: CommandFlags, fragment: FunctionFragment, args, callvalue=0):
        self.contract = contract
        self.flags = flags
        self.fragment = fragment
        self.args = args
        self.callvalue = callvalue

    def withValue(self, value):
        """
        Returns a new [[FunctionCall]] that sends value with the call.
        @param value The value (in wei) to send with the call
        """
        if (self.flags & CommandFlags.CALLTYPE_MASK) != CommandFlags.CALL and (
            self.flags & CommandFlags.CALLTYPE_MASK
        ) != CommandFlags.CALL_WITH_VALUE:
            raise ValueError("Only CALL operations can send value")
        return self.__class__(
            self.contract,
            (self.flags & ~CommandFlags.CALLTYPE_MASK) | CommandFlags.CALL_WITH_VALUE,
            self.fragment,
            self.args,
            eth_abi.encode_single("uint", value),
        )

    def rawValue(self):
        """
        Returns a new [[FunctionCall]] whose return value will be wrapped as a `bytes`.
        This permits capturing the return values of functions with multiple return parameters,
        which weiroll does not otherwise support.
        """
        return self.__class__(
            self.contract,
            self.flags | CommandFlags.TUPLE_RETURN,
            self.fragment,
            self.args,
            self.callvalue,
        )

    def staticcall(self):
        """Returns a new [[FunctionCall]] that executes a STATICCALL instead of a regular CALL."""
        if (self.flags & CommandFlags.CALLTYPE_MASK) != CommandFlags.CALL:
            raise ValueError("Only CALL operations can be made static")
        return self.__class__(
            self.contract,
            (self.flags & ~CommandFlags.CALLTYPE_MASK) | CommandFlags.STATICCALL,
            self.fragment,
            self.args,
            self.callvalue,
        )


def isDynamicType(param) -> bool:
    return eth_abi.grammar.parse(param).is_dynamic


def encodeArg(arg, param):
    if isValue(arg):
        if arg.param != param:
            raise ValueError(f"Cannot pass value of type ${arg.param} to input of type ${param}")
        return arg
    if isinstance(arg, WeirollPlanner):
        return SubplanValue(arg)
    return LiteralValue(param, eth_abi.encode_single(param, arg))


class WeirollContract:
    """
    * Provides a dynamically created interface to interact with Ethereum contracts via weiroll.
    *
    * Once created using the constructor or the [[Contract.createContract]] or [[Contract.createLibrary]]
    * functions, the returned object is automatically populated with methods that match those on the
    * supplied contract. For instance, if your contract has a method `add(uint, uint)`, you can call it on the
    * [[Contract]] object:
    * ```typescript
    * // Assumes `Math` is an ethers.js Contract instance.
    * const math = Contract.createLibrary(Math);
    * const result = math.add(1, 2);
    * ```
    *
    * Calling a contract function returns a [[FunctionCall]] object, which you can pass to [[Planner.add]],
    * [[Planner.addSubplan]], or [[Planner.replaceState]] to add to the sequence of calls to plan.
    """

    def __init__(self, brownieContract: brownie.Contract, commandFlags: CommandFlags = 0):
        self.brownieContract = brownieContract
        self.address = brownieContract.address

        self.commandFlags = commandFlags
        self.functions = {}  # aka functionsBySelector
        self.functionsBySignature = {}
        self.fragmentsBySelector = {}

        selectorsByName = defaultdict(list)

        for selector, name in self.brownieContract.selectors.items():
            fragment = FunctionFragment(self.brownieContract, selector)

            # Check that the signature is unique; if not the ABI generation has
            # not been cleaned or may be incorrectly generated
            if selector in self.functions:
                raise ValueError(f"Duplicate ABI entry for selector: {selector}")

            self.fragmentsBySelector[selector] = fragment

            plan_fn = buildCall(self, fragment)

            # save this plan helper function fragment in self.functions
            self.functions[selector] = plan_fn

            # make the plan helper function available on self by selector
            setattr(self, selector, plan_fn)

            # Track unique names; we only expose bare named functions if they are ambiguous
            selectorsByName[name].append(selector)

        self.functionsByUniqueName = {}

        for name, selectors in selectorsByName.items():
            # Ambiguous names to not get attached as bare names
            if len(selectors) == 1:
                if hasattr(self, name):
                    # TODO: i think this is impossible
                    raise ValueError("duplicate name!")

                plan_fn = self.functions[selectors[0]]

                # make the plan helper function available on self
                setattr(self, name, plan_fn)
                self.functionsByUniqueName[name] = plan_fn
            else:
                # define a new function which will use brownie' get_fn_from_args
                # to decide which plan_fn to route to
                def _overload(*args, fn_name=name):
                    overload_method = self.brownieContract.__getattribute__(fn_name)
                    method = overload_method._get_fn_from_args(args)
                    signature = method.signature
                    plan_fn = self.functions[signature]
                    return plan_fn(*args)

                setattr(self, name, _overload)

            # attach full signatures (for methods with duplicate names)
            for selector in selectors:
                fragment = self.fragmentsBySelector[selector]

                signature = name + "(" + ",".join(fragment.inputs) + ")"

                plan_fn = self.functions[selector]

                self.functionsBySignature[signature] = plan_fn


    @classmethod
    @cache
    def createContract(
        cls,
        contract: brownie.Contract,
        commandflags=CommandFlags.CALL,
    ):
        """
        Creates a [[Contract]] object from an ethers.js contract.
        All calls on the returned object will default to being standard CALL operations.
        Use this when you want your weiroll script to call a standard external contract.
        @param contract The ethers.js Contract object to wrap.
        @param commandflags Optionally specifies a non-default call type to use, such as
                [[CommandFlags.STATICCALL]].
        """
        assert commandflags != CommandFlags.DELEGATECALL
        return cls(
            contract,
            commandflags,
        )

    @classmethod
    @cache
    def createLibrary(
        cls,
        contract: brownie.Contract,
    ):
        """
        * Creates a [[Contract]] object from an ethers.js contract.
        * All calls on the returned object will default to being DELEGATECALL operations.
        * Use this when you want your weiroll script to call a library specifically designed
        * for use with weiroll.
        * @param contract The ethers.js Contract object to wrap.
        """
        return cls(contract, CommandFlags.DELEGATECALL)

    # TODO: port getInterface?


# TODO: not sure about this one. this was just how the javascript code worked, but can probably be refactored
def buildCall(contract: WeirollContract, fragment: FunctionFragment):
    def _call(*args) -> FunctionCall:
        if len(args) != len(fragment.inputs):
            raise ValueError(f"Function {fragment.name} has {len(fragment.inputs)} arguments but {len(args)} provided")

        # TODO: maybe this should just be fragment.encode_args()
        encodedArgs = fragment.encode_args(*args)

        return FunctionCall(
            contract,
            contract.commandFlags,
            fragment,
            encodedArgs,
        )

    return _call


class CommandType(IntEnum):
    CALL = 1
    RAWCALL = 2
    SUBPLAN = 3


Command = namedtuple("Command", "call,type")


# returnSlotMap: Maps from a command to the slot used for its return value
# literalSlotMap: Maps from a literal to the slot used to store it
# freeSlots: An array of unused state slots
# stateExpirations: Maps from a command to the slots that expire when it's executed
# commandVisibility: Maps from a command to the last command that consumes its output
# state: The initial state array
PlannerState = namedtuple(
    "PlannerState",
    "returnSlotMap, literalSlotMap, freeSlots, stateExpirations, commandVisibility, state",
)


def padArray(a, length, padValue) -> list:
    return a + [padValue] * (length - len(a))


class WeirollPlanner:
    def __init__(self, clone):
        self.state = StateValue()
        self.commands: list[Command] = []
        self.unlimited_approvals = set()

        self.clone = clone

    def approve(self, token: brownie.Contract, spender: str, wei_needed, approve_wei=None) -> Optional[ReturnValue]:
        key = (token, self.clone, spender)

        if approve_wei is None:
            approve_wei = MAX_UINT256

        if key in self.unlimited_approvals and approve_wei != 0:
            # we already planned an infinite approval for this token (and we aren't trying to set the approval to 0)
            return

        # check current allowance
        if token.allowance(self.clone, spender) >= wei_needed:
            return

        if approve_wei == MAX_UINT256:
            self.unlimited_approvals.add(key)

        return self.call(token, "approve", spender, approve_wei)

    def call(self, brownieContract: brownie.Contract, func_name, *args):
        """func_name can be just the name, or it can be the full signature.

        If there are multiple functions with the same name, you must use the signature.

        TODO: brownie has some logic for figuring out which overloaded method to use. we should use that here
        """
        weirollContract = WeirollContract.createContract(brownieContract)

        if func_name.endswith(")"):
            # TODO: would be interesting to look at args and do this automatically
            func = weirollContract.functionsBySignature[func_name]
        else:
            func = weirollContract.functionsByUniqueName[func_name]

        return self.add(func(*args))

    def delegatecall(self, brownieContract: brownie.Contract, func_name, *args):
        contract = WeirollContract.createLibrary(brownieContract)

        if func_name in contract.functionsByUniqueName:
            func = contract.functionsByUniqueName[func_name]
        elif func_name in contract.functionsBySignature:
            func = contract.functionsBySignature[func_name]
        else:
            # print("func_name:", func_name)
            # print("functionsByUniqueName:", contract.functionsByUniqueName)
            # print("functionsBySignature:", contract.functionsBySignature)
            raise ValueError(f"Unknown func_name ({func_name}) on {brownieContract}")

        return self.add(func(*args))

    def add(self, call: FunctionCall) -> Optional[ReturnValue]:
        """
        * Adds a new function call to the planner. Function calls are executed in the order they are added.
        *
        * If the function call has a return value, `add` returns an object representing that value, which you
        * can pass to subsequent function calls. For example:
        * ```typescript
        * const math = Contract.createLibrary(Math); // Assumes `Math` is an ethers.js contract object
        * const events = Contract.createLibrary(Events); // Assumes `Events` is an ethers.js contract object
        * const planner = new Planner();
        * const sum = planner.add(math.add(21, 21));
        * planner.add(events.logUint(sum));
        * ```
        * @param call The [[FunctionCall]] to add to the planner
        * @returns An object representing the return value of the call, or null if it does not return a value.
        """
        command = Command(call, CommandType.CALL)
        self.commands.append(command)

        for arg in call.args:
            if isinstance(arg, SubplanValue):
                raise ValueError("Only subplans can have arguments of type SubplanValue")

        if call.flags & CommandFlags.TUPLE_RETURN:
            return ReturnValue("bytes", command)

        # TODO: test this more
        if len(call.fragment.outputs) != 1:
            return None

        # print("call fragment outputs", call.fragment.outputs)

        return ReturnValue(call.fragment.outputs[0], command)

    def subcall(self, brownieContract: brownie.Contract, func_name, *args):
        """
        * Adds a call to a subplan. This has the effect of instantiating a nested instance of the weiroll
        * interpreter, and is commonly used for functionality such as flashloans, control flow, or anywhere
        * else you may need to execute logic inside a callback.
        *
        * A [[FunctionCall]] passed to [[Planner.addSubplan]] must take another [[Planner]] object as one
        * argument, and a placeholder representing the planner state, accessible as [[Planner.state]], as
        * another. Exactly one of each argument must be provided.
        *
        * At runtime, the subplan is replaced by a list of commands for the subplanner (type `bytes32[]`),
        * and `planner.state` is replaced by the current state of the parent planner instance (type `bytes[]`).
        *
        * If the `call` returns a `bytes[]`, this will be used to replace the parent planner's state after
        * the call to the subplanner completes. Return values defined inside a subplan may be used outside that
        * subplan - both in the parent planner and in subsequent subplans - only if the `call` returns the
        * updated planner state.
        *
        * Example usage:
        * ```
        * const exchange = Contract.createLibrary(Exchange); // Assumes `Exchange` is an ethers.js contract
        * const events = Contract.createLibrary(Events); // Assumes `Events` is an ethers.js contract
        * const subplanner = new Planner();
        * const outqty = subplanner.add(exchange.swap(tokenb, tokena, qty));
        *
        * const planner = new Planner();
        * planner.addSubplan(exchange.flashswap(tokena, tokenb, qty, subplanner, planner.state));
        * planner.add(events.logUint(outqty)); // Only works if `exchange.flashswap` returns updated state
        * ```
        * @param call The [[FunctionCall]] to add to the planner.
        """
        contract = WeirollContract.createContract(brownieContract)
        func = getattr(contract, func_name)
        func_call = func(*args)
        return self.addSubplan(func_call)

    def subdelegatecall(self, brownieContract: brownie.Contract, func_name, *args):
        contract = WeirollContract.createLibrary(brownieContract)
        func = getattr(contract, func_name)
        func_call = func(*args)
        return self.addSubplan(func_call)

    def addSubplan(self, call: FunctionCall):
        hasSubplan = False
        hasState = False

        for arg in call.args:
            if isinstance(arg, SubplanValue):
                if hasSubplan:
                    raise ValueError("Subplans can only take one planner argument")
                hasSubplan = True
            elif isinstance(arg, StateValue):
                if hasState:
                    raise ValueError("Subplans can only take one state argument")
                hasState = True
        if not hasSubplan or not hasState:
            raise ValueError("Subplans must take planner and state arguments")
        if call.fragment.outputs and len(call.fragment.outputs) == 1 and call.fragment.outputs[0] != "bytes[]":
            raise ValueError("Subplans must return a bytes[] replacement state or nothing")

        self.commands.append(Command(call, CommandType.SUBPLAN))

    def replaceState(self, call: FunctionCall):
        """
        * Executes a [[FunctionCall]], and replaces the planner state with the value it
        * returns. This can be used to execute functions that make arbitrary changes to
        * the planner state. Note that the planner library is not aware of these changes -
        * so it may produce invalid plans if you don't know what you're doing.
        * @param call The [[FunctionCall]] to execute
        """
        if (call.fragment.outputs and len(call.fragment.outputs) != 1) or call.fragment.outputs[0] != "bytes[]":
            raise ValueError("Function replacing state must return a bytes[]")
        self.commands.append(Command(call, CommandType.RAWCALL))

    def _preplan(self, commandVisibility, literalVisibility, seen=None, planners=None):
        if seen is None:
            seen: set[Command] = set()
        if planners is None:
            planners: set[WeirollPlanner] = set()

        if self in planners:
            raise ValueError("A planner cannot contain itself")
        planners.add(self)

        # Build visibility maps
        for command in self.commands:
            inargs = command.call.args
            if command.call.flags & CommandFlags.CALLTYPE_MASK == CommandFlags.CALL_WITH_VALUE:
                if not command.call.callvalue:
                    raise ValueError("Call with value must have a value parameter")
                inargs = [command.call.callvalue] + inargs

            for arg in inargs:
                if isinstance(arg, ReturnValue):
                    if not arg.command in seen:
                        raise ValueError(f"Return value from '{arg.command.call.fragment.name}' is not visible here")
                    commandVisibility[arg.command] = command
                elif isinstance(arg, LiteralValue):
                    literalVisibility[arg.value] = command
                elif isinstance(arg, SubplanValue):
                    subplanSeen = seen  # do not copy
                    if not command.call.fragment.outputs:
                        # Read-only subplan; return values aren't visible externally
                        subplanSeen = set(seen)
                    arg.planner._preplan(commandVisibility, literalVisibility, subplanSeen, planners)
                elif not isinstance(arg, StateValue):
                    raise ValueError(f"Unknown function argument type '{arg}'")

            seen.add(command)

        return commandVisibility, literalVisibility

    def _buildCommandArgs(self, command: Command, returnSlotMap, literalSlotMap, state):
        # Build a list of argument value indexes
        inargs = command.call.args
        if command.call.flags & CommandFlags.CALLTYPE_MASK == CommandFlags.CALL_WITH_VALUE:
            if not command.call.callvalue:
                raise ValueError("Call with value must have a value parameter")
            inargs = [command.call.callvalue] + inargs

        args: list[int] = []
        for arg in inargs:
            if isinstance(arg, ReturnValue):
                slot = returnSlotMap[arg.command]
            elif isinstance(arg, LiteralValue):
                slot = literalSlotMap[arg.value]
            elif isinstance(arg, StateValue):
                slot = 0xFE
            elif isinstance(arg, SubplanValue):
                # buildCommands has already built the subplan and put it in the last state slot
                slot = len(state) - 1
            else:
                raise ValueError(f"Unknown function argument type {arg}")
            if isDynamicType(arg.param):
                slot |= 0x80
            args.append(slot)

        return args

    def _buildCommands(self, ps: PlannerState) -> list[str]:
        encodedCommands = []
        for command in self.commands:
            if command.type == CommandType.SUBPLAN:
                # find the subplan
                subplanner = next(arg for arg in command.call.args if isinstance(arg, SubplanValue)).planner
                subcommands = subplanner._buildCommands(ps)
                ps.state.append(HexBytes(eth_abi.encode_single("bytes32[]", subcommands))[32:])
                # The slot is no longer needed after this command
                ps.freeSlots.append(len(ps.state) - 1)

            flags = command.call.flags

            args = self._buildCommandArgs(command, ps.returnSlotMap, ps.literalSlotMap, ps.state)

            if len(args) > 6:
                flags |= CommandFlags.EXTENDED_COMMAND

            # Add any newly unused state slots to the list
            ps.freeSlots.extend(ps.stateExpirations[command])

            ret = 0xFF
            if command in ps.commandVisibility:
                if command.type in [CommandType.RAWCALL, CommandType.SUBPLAN]:
                    raise ValueError(
                        f"Return value of {command.call.fragment.name} cannot be used to replace state and in another function"
                    )
                ret = len(ps.state)

                if len(ps.freeSlots) > 0:
                    ret = ps.freeSlots.pop()

                # store the slot mapping
                ps.returnSlotMap[command] = ret

                # make the slot available when it's not needed
                expiryCommand = ps.commandVisibility[command]
                ps.stateExpirations[expiryCommand].append(ret)

                if ret == len(ps.state):
                    ps.state.append(b"")

                if (
                    command.call.fragment.outputs and isDynamicType(command.call.fragment.outputs[0])
                ) or command.call.flags & CommandFlags.TUPLE_RETURN != 0:
                    ret |= 0x80
            elif command.type in [CommandType.RAWCALL, CommandType.SUBPLAN]:
                if command.call.fragment.outputs and len(command.call.fragment.outputs) == 1:
                    ret = 0xFE

            if flags & CommandFlags.EXTENDED_COMMAND == CommandFlags.EXTENDED_COMMAND:
                # extended command
                encodedCommands.extend(
                    [
                        hexConcat(
                            command.call.fragment.signature,
                            flags,
                            [0xFF] * 6,
                            ret,
                            command.call.contract.address,
                        ),
                        hexConcat(padArray(args, 32, 0xFF)),
                    ]
                )
            else:
                # standard command
                encodedCommands.append(
                    hexConcat(
                        command.call.fragment.signature,
                        flags,
                        padArray(args, 6, 0xFF),
                        ret,
                        command.call.contract.address,
                    )
                )
        return encodedCommands

    def plan(self) -> tuple[list[str], list[str]]:
        # Tracks the last time a literal is used in the program
        literalVisibility: dict[str, Command] = {}
        # Tracks the last time a command's output is used in the program
        commandVisibility: dict[Command, Command] = {}

        self._preplan(commandVisibility, literalVisibility)

        # Maps from commands to the slots that expire on execution (if any)
        stateExpirations: dict[Command, list[int]] = defaultdict(list)

        # Tracks the state slot each literal is stored in
        literalSlotMap: dict[str, int] = {}

        state: list[str] = []

        # Prepopulate the state and state expirations with literals
        for (literal, lastCommand) in literalVisibility.items():
            slot = len(state)
            state.append(literal)
            literalSlotMap[literal] = slot
            stateExpirations[lastCommand].append(slot)

        ps: PlannerState = PlannerState(
            returnSlotMap={},
            literalSlotMap=literalSlotMap,
            freeSlots=[],
            stateExpirations=stateExpirations,
            commandVisibility=commandVisibility,
            state=state,
        )

        encodedCommands = self._buildCommands(ps)

        return encodedCommands, state
