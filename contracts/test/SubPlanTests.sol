// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

import "../VM.sol";

contract TestSubplan is VM {
    function execute(bytes32[] calldata commands, bytes[] memory state)
        public
        payable
        returns (bytes[] memory)
    {
        return _execute(commands, state);
    }
}

contract TestReadonlySubplan is VM {
    function execute(bytes32[] calldata commands, bytes[] memory state)
        public
        payable
    {
        _execute(commands, state);
    }
}

contract TestMultiSubplan is VM {
    function execute(
        bytes32[] calldata commands,
        bytes32[] calldata commands2,
        bytes[] memory state
    ) public payable returns (bytes[] memory) {
        state = _execute(commands, state);
        state = _execute(commands2, state);
        return state;
    }
}

contract TestMultiStateSubplan is VM {
    function execute(
        bytes32[] calldata commands,
        bytes[] memory state,
        bytes[] memory state2
    ) public payable returns (bytes[] memory) {
        _execute(commands, state);
        return _execute(commands, state2);
    }
}

contract TestBadSubplan is VM {
    function execute(bytes32[] calldata commands, bytes[] memory state)
        public
        payable
        returns (int256)
    {
        _execute(commands, state);
        return 0;
    }
}
