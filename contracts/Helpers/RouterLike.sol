// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;


contract RouterLike {
    SwapDescription public saved;
    SwapDescription public savedSimple;
    struct SwapDescription {
        address srcToken;
        address dstToken;
        address payable srcReceiver;
        address payable dstReceiver;
        uint256 amount;
        uint256 minReturnAmount;
        uint256 flags;
        bytes permit;
    }

    function swap(
        address caller,
        SwapDescription calldata desc,
        bytes calldata data
    ) public {
        saved = desc;
    }

    function swapSimple(
        SwapDescription calldata desc
    ) public {
        savedSimple = desc;
}
}
