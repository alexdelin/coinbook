#!/usr/bin/env python
"""
CoinBook - Lightweight components for
managing cryptocurrency investments

Implements a class CoinBook, which is the main
access point for all functionality

Stores all required data in redis
"""

import json
import hashlib
from datetime import datetime

import redis

from bittrex import Bittrex, API_V1_1


class CoinBook(object):
    """CoinBook"""

    def __init__(self, initial_funds=None, reset_funds=False,
                 redis_password=None):

        super(CoinBook, self).__init__()

        self.bittrex_client = Bittrex(None, None, api_version=API_V1_1)
        self.redis = redis.StrictRedis(
            host='localhost', port=6379, db=0, password=redis_password)

        # Set details for funds if they aren't already there
        funds_details = self.redis.get('coinbook-funds')
        if not funds_details or reset_funds:
            if not initial_funds:
                raise ValueError('You do not have any funds, set some '
                                 'with initial_funds to get started')
            self.set_funds(initial_funds)

    def get_funds(self):
        """Get the details of the current funds held by the user
        returned in units of BTC
        """

        funds_data = json.loads(self.redis.get('coinbook-funds'))
        funds_amt = funds_data.get('amount')
        return funds_amt

    def set_funds(self, amount):
        """Updates the amount of funds to the specified amount
        Always must be done in units of BTC
        """

        funds_data = {
            "amount": amount,
            "units": "BTC"
        }
        self.redis.set('coinbook-funds', json.dumps(funds_data))

    def convert_units(self, amount, source_currency, target_currency):
        """Converts value of a given amount from one currency into
        another. Uses the current market prices to do so
        """

        # Validate arguments
        if not isinstance(amount, float):
            amount = float(amount)
        if source_currency != 'BTC' and target_currency != 'BTC':
            raise ValueError('One of the currencies must be Bitcoin')

        # Get conversion Factor
        if source_currency == 'BTC':

            ticker = 'BTC-{target}'.format(target=target_currency)
            ticker_data = self.bittrex_client.get_ticker(ticker)
            exchange_rate = ticker_data.get('result', {}).get('Last')
            if not exchange_rate:
                raise ValueError('Invalid Exchange Rate')
            return amount / exchange_rate

        else:
            # The Target currency is BTC
            ticker = 'BTC-{source}'.format(source=source_currency)
            ticker_data = self.bittrex_client.get_ticker(ticker)
            exchange_rate = ticker_data.get('result', {}).get('Last')
            if not exchange_rate:
                raise ValueError('Invalid Exchange Rate')
            return amount * exchange_rate

    def crawl(self):
        """Crawl the market to look for buying opportunities
        """

        summaries = self.bittrex_client.get_market_summaries()
        all_coins = summaries.get('result')

        for coin in all_coins:

            trade = self.evaluate_coin(coin)
            if trade:

                self.make_buy(
                    currency=trade.get('currency'),
                    amount=trade.get('amount'))

    def make_buy(self, currency, amount):
        """Make a given trade with the provided parameters
        Updates the amount of funds remaining, and
        creates a new position for the new buy if needed
        :amount is the amount in units of the desired currency
        """

        # Create the new position
        current_timestamp = datetime.now().isoformat()
        m = hashlib.sha256()
        m.update(currency)
        m.update(current_timestamp)
        pos_hash = m.hexdigest()[:20]
        position_key = 'coinbook-position-{pos_hash}'.format(pos_hash=pos_hash)

        position_data = {
            "currency": currency,
            "amount": amount,
            "open_timestamp": current_timestamp
        }

        self.redis.set(position_key, json.dumps(position_data))

        # Subtract the needed funds from our BTC balance
        current_funds = self.get_funds()
        transaction_value_btc = self.convert_units(amount, currency, 'BTC')
        new_funds = current_funds - transaction_value_btc
        self.set_funds(new_funds)

    def make_sell(self, position_id):
        """Close out a given position.
        The ID passed in is the redis key that holds the position
        """

        # Get position details
        pos_data = json.loads(self.redis.get(position_id))
        pos_currency = pos_data.get('currency')
        pos_amount = pos_data.get('amount')

        # Delete existing position
        self.redis.delete(position_id)

        # Update funds data
        pos_value_btc = self.convert_units(pos_amount, pos_currency, 'BTC')
        current_funds = self.get_funds()
        new_funds = current_funds + pos_value_btc
        self.set_funds(new_funds)
        pass

    def evaluate_coin(self, coin):
        """Evaluate a coin and determine if it should be
        purchased or not
        returns None if no trade should be made
        returns a dictionary if a trade should be made
            the dictionary should include the keys:
            * "currency" - the currency code
            * "amount" - the amount in units of the currency
        """

        raise NotImplementedError('This should be implemented with the '
                                  'specific strategy you want to test')

    def evaluate_all_positions(self):
        """Evaluate all current positions to check if
        they should be held or closed out
        """

        all_positions = self.redis.keys(pattern='coinbook-position-*')

        for position in all_positions:
            self.evaluate_position(position)

    def evaluate_position(self, position):
        """Evaluate a single position currently held.
        The position value passed in is the redis key
        to get the position details
        """

        pass

    def get_total_balance(self):
        """Gets the total account balance across
        all held positions and funds
        Returns an answer in units of BTC
        """

        # Get funds balance
        funds_balance = self.get_funds()

        # Get positions balance
        all_positions = self.redis.keys(pattern='coinbook-position-*')
        position_balances = []

        for position in all_positions:
            pos_data = json.loads(self.redis.get(position))
            pos_currency = pos_data.get('currency')
            pos_amount = pos_data.get('amount')
            pos_value_btc = self.convert_units(pos_amount, pos_currency, 'BTC')
            position_balances.append(pos_value_btc)

        # Get total balance
        total_balance = funds_balance + sum(position_balances)
        return total_balance
