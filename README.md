# weiroll-py

weiroll-py is a planner for the operation-chaining/scripting language [weiroll](https://github.com/weiroll/weiroll).
weiroll-py is inspired by [weiroll.js](https://github.com/weiroll/weiroll.js).

It provides an easy-to-use API for generating weiroll programs that can then be passed to any compatible implementation.

## Installation

```
pip install weiroll-py==0.2.0
```

where 0.2.0 is the latest version.

## Usage

### Wrapping contracts
Weiroll programs consist of a sequence of calls to functions in external contracts. These calls can either be delegate calls to dedicated library contracts, or standard/static calls to external contracts. Before you can start creating a weiroll program, you will need to create interfaces for at least one contract you intend to use.

The easiest way to do this is by wrapping brownie contract instances:

```python
brownie_contract = brownie.Contract(address)
contract = weiroll.WeirollContract(
  brownie_contract
)
```

This will produce a contract object that generates delegate calls to the brownie contract in `WeirollContract`.

To create delegate to an external contract, use `createLibrary`:

```python
brownie_contract = brownie.Contract(address)
# Makes calls using CALL
contract = weiroll.WeirollContract.createContract(brownie_contract)
# Makes calls using STATICCALL
contract = weiroll.WeirollContract.createContract(brownie_contract, weiroll.CommandFlags.STATICCALL)
```

You can repeat this for each contract you wish to use. A weiroll `WeirollContract` object can be reused across as many planner instances as you wish; there is no need to construct them again for each new program.

### Planning programs

First, instantiate a planner:

```python
planner = weiroll.WeirollPlanner()
```

Next, add one or more commands to execute:

```python
ret = planner.add(contract.func(a, b))
```

Return values from one invocation can be used in another one:

```python
planner.add(contract.func2(ret))
```

Remember to wrap each call to a contract in `planner.add`. Attempting to pass the result of one contract function directly to another will not work - each one needs to be added to the planner!

For calls to external contracts, you can also pass a value in ether to send:

```python
planner.add(contract.func(a, b).withValue(c))
```

`withValue` takes the same argument types as contract functions, so you can pass the return value of another function, or a literal value. You cannot combine `withValue` with delegate calls (eg, calls to a library created with `Contract.newLibrary`) or static calls.

Likewise, if you want to make a particular call static, you can use `.staticcall()`:

```python
result = planner.add(contract.func(a, b).staticcall())
```

Weiroll only supports functions that return a single value by default. If your function returns multiple values, though, you can instruct weiroll to wrap it in a `bytes`, which subsequent commands can decode and work with:

```python
ret = planner.add(contract.func(a, b).rawValue())
```

Once you are done planning operations, generate the program:

```python
commands, state = planner.plan()
```

### Subplans
In some cases it may be useful to be able to instantiate nested instances of the weiroll VM - for example, when using flash loans, or other systems that function by making a callback to your code. The weiroll planner supports this via 'subplans'.

To make a subplan, construct the operations that should take place inside the nested instance normally, then pass the planner object to a contract function that executes the subplan, and pass that to the outer planner's `.addSubplan()` function instead of `.add()`.

For example, suppose you want to call a nested instance to do some math:

```python
subplanner = WeirollPlanner()
sum = subplanner.add(Math.add(1, 2))

planner = WeirollPlanner()
planner.addSubplan(Weiroll.execute(subplanner, subplanner.state))
planner.add(events.logUint(sum))

commands, state = planner.plan()
```

Subplan functions must specify which argument receives the current state using the special variable `Planner.state`, and must take exactly one subplanner and one state argument. Subplan functions must either return an updated state or nothing.

If a subplan returns updated state, return values created in a subplanner, such as `sum` above, can be referenced in the outer scope, and even in other subplans, as long as they are referenced after the command that produces them. Subplans that do not return updated state are read-only, and return values defined inside them cannot be referenced outside them.

## More examples

Review [tests](/tests) for more examples.

## Credits

- [@WyseNynja](https://github.com/WyseNynja) for the original implementation
