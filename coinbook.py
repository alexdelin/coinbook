#!/usr/bin/env python
"""
CoinBook - Lightweight components for
managing cryptocurrency investments

Implements a class CoinBook, which is the main
access point for all functionality

Stores all required data in redis
"""

import json

import requests
import redis

from bittrex import Bittrex, API_V2_0


class CoinBook(object):
    """CoinBook"""

    def __init__(self, initial_funds=None, reset_funds=False,
                 redis_password=None):

        super(CoinBook, self).__init__()

        self.bittrex_client = Bittrex(None, None, api_version=API_V2_0)
        self.redis = redis.StrictRedis(
            host='localhost', port=6379, db=0, password=redis_password)

        # Set details for funds if they aren't already there
        funds_details = self.redis.get('coinbook_funds')
        if not funds_details or reset_funds:
            if not initial_funds:
                raise ValueError('You do not have any funds, set some '\
                                 'with initial_funds to get started')
            self.set_funds(initial_funds)

    def get_funds(self):
        """Get the details of the current funds held by the user
        """

        pass

    def set_funds(self, amount):
        """Updates the amount of funds to the specified amount
        """

        pass

    def crawl(self):
        """Crawl the market to look for buying opportunities
        """

        summaries = self.bittrex_client.get_market_summaries()
        all_coins = summaries.get('result')

        self.update_btc_base()

        for coin in all_coins:

            trade = self.evaluate_coin(coin)
            if trade:

                self.make_trade(
                    currency=trade.get('currency'),
                    amount=trade.get('amount'),
                    action=trade.get('action'))

    def update_btc_base(self):
        """Update the base price of bitcoin.
        This is necessary because we only deal with prices in USD
        to avoid the effects of fluctuations in the price of BTC
        on the valuations of other coins.
        As all other coins are priced in units of BTC, we want to
        make sure that we have the most up-to-date prices in USD
        available
        """

        pass


    def make_trade(self, currency, amount, action):
        """Make a given trade with the provided parameters

        returns None if no trade should be made
        returns a dictionary if a trade should be made
            the dictionary should include the keys:
            * "currency" - the currency code
            * "amount" - the amount in units of the currency
            * "action" - one of ("buy, "sell")
        """

        pass

    def evaluate_coin(self):
        """Evaluate a coin and determine if it should be
        purchased or not
        """

        raise NotImplementedError('This should be implemented with the '\
                                  'specific strategy you want to test')


    def evaluate_positions(self):
        """Evaluate all current positions to check if
        they should be held or closed out
        """

        pass

    def get_total_balance(self):
        """Gets the total account balance across
        all held positions and funds
        """

        pass
