from brownie import Contract, accounts, Wei, chain, TestableVM
from weiroll import WeirollContract, WeirollPlanner, ReturnValue
import requests


def test_chaining_action():

    settlement_address = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
    c = Contract.from_explorer(settlement_address)
    wc = WeirollContract(c)
