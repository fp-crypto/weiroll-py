// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

import "../VM.sol";

contract TestableVMWithMath is VM {
    function execute(bytes32[] calldata commands, bytes[] memory state)
        public
        payable
        returns (bytes[] memory)
    {
        return _execute(commands, state);
    }

    function sum(uint256 a, uint256 b) public pure returns (uint256) {
        return a + b;
    }

    function sum3(uint256 a, uint256 b, uint256 c) public pure returns (uint256) {
        return a + b;
    }

    function sub(uint256 a, uint256 b) public pure returns (uint256) {
        return a - b;
    }


    function dispatch(bytes memory inputs)
        internal
        override
        returns (bool _success, bytes memory _ret)
    {
        bytes4 _selector = bytes4(bytes32(inputs));
        if (this.sum.selector == _selector) {
            uint256 a;
            uint256 b;
            assembly {
                a := mload(add(inputs, 36))
                b := mload(add(inputs, 68))
            }
            uint256 res = sum(a, b);
            _ret = new bytes(32);
            assembly {
                mstore(add(_ret, 32), res)
            }
            return (true, _ret);
        }
        if (this.sub.selector == _selector) {
            uint256 a;
            uint256 b;
            assembly {
                a := mload(add(inputs, 36))
                b := mload(add(inputs, 68))
            }
            uint256 res = sub(a, b);
            _ret = new bytes(32);
            assembly {
                mstore(add(_ret, 32), res)
            }
            return (true, _ret);
        }
        if (this.sum3.selector == _selector) {
            uint256 a;
            uint256 b;
            uint256 c;
            assembly {
                a := mload(add(inputs, 36))
                b := mload(add(inputs, 68))
                c := mload(add(inputs, 100))
            }
            uint256 res = sum3(a, b, c);
            _ret = new bytes(32);
            assembly {
                mstore(add(_ret, 32), res)
            }
            return (true, _ret);
        }
    }
}