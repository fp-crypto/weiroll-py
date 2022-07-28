// SPDX-License-Identifier: MIT
pragma solidity ^0.8.12;

import '../Libraries/UniswapV3/LiquidityAmounts.sol';
import '../Libraries/UniswapV3/TickMath.sol';
import {IUniswapV3Pool} from "@uniswap/contracts/interfaces/IUniswapV3Pool.sol";


contract UniswapV3Helper {

    function getLPAmount(
        address pool,
        int24 minTick,
        int24 maxTick,
        uint256 maxToken0Amount,
        uint256 maxToken1Amount
    ) public view returns (uint256, uint256) {
      
        (uint160 sqrtRatioX96,,,,,,) = IUniswapV3Pool(pool).slot0();

        uint160 sqrtRatioAX96 = TickMath.getSqrtRatioAtTick(minTick);
        uint160 sqrtRatioBX96 = TickMath.getSqrtRatioAtTick(maxTick);

        if (sqrtRatioAX96 > sqrtRatioBX96) (sqrtRatioAX96, sqrtRatioBX96) = (sqrtRatioBX96, sqrtRatioAX96);

        if (sqrtRatioX96 <= sqrtRatioAX96) {
            return (maxToken0Amount, 0);
        } else if (sqrtRatioX96 < sqrtRatioBX96) {
            uint128 liquidity0 = LiquidityAmounts.getLiquidityForAmount0(sqrtRatioX96, sqrtRatioBX96, maxToken0Amount);
            uint128 liquidity1 = LiquidityAmounts.getLiquidityForAmount1(sqrtRatioAX96, sqrtRatioX96, maxToken1Amount);

            if (liquidity0 < liquidity1) {
                return (maxToken0Amount, LiquidityAmounts.getAmount1ForLiquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity0));
            } else {
                return (LiquidityAmounts.getAmount0ForLiquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity1), maxToken1Amount);
            }
        } else {
            return (0, maxToken1Amount);
        }
    }

    function getLPAmount0(
        address pool,
        int24 minTick,
        int24 maxTick,
        uint256 maxToken0Amount,
        uint256 maxToken1Amount
    ) external view returns (uint256 amount0) {
        (amount0,) = getLPAmount(pool, minTick, maxTick, maxToken0Amount, maxToken1Amount);
    }

    function getLPAmount1(
        address pool,
        int24 minTick,
        int24 maxTick,
        uint256 maxToken0Amount,
        uint256 maxToken1Amount
    ) external view returns (uint256 amount1) {
        (, amount1) = getLPAmount(pool, minTick, maxTick, maxToken0Amount, maxToken1Amount);
    }
}

