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

from bittrex import Bittrex, API_V1_1, API_V2_0


class CoinBook(object):
    """CoinBook"""

    def __init__(self, strategy_name='empty', initial_funds=None,
                 reset_funds=False, redis_password=None):

        super(CoinBook, self).__init__()

        self.bittrex_20_client = Bittrex(None, None, api_version=API_V2_0)
        self.bittrex_11_client = Bittrex(None, None, api_version=API_V1_1)
        self.strategy_name = strategy_name
        self.redis = redis.StrictRedis(
            host='localhost', port=6379, db=0, password=redis_password)

        # Set details for funds if they aren't already there
        funds_details = self.redis.get('coinbook-{strategy}-funds'.format(
                                            strategy=self.strategy_name))

        if not funds_details or reset_funds:
            if not initial_funds:
                raise ValueError('You do not have any funds, set some '
                                 'with initial_funds to get started')
            # Try to clear out any existing redis keys, just to be safe
            self.clear_redis_keys()
            self.set_funds(initial_funds)

    def clear_redis_keys(self):
        """Clear out any redis keys which appear to be owned by
        the current strategy.
        """

        all_keys = self.redis.keys(
            pattern='coinbook-{strategy}-*'.format(
                        strategy=self.strategy_name))

        for redis_key in all_keys:
            self.redis.delete(redis_key)

    def get_positions(self):
        """Gets all currently open positions
        """

        all_positions = self.redis.keys(
            pattern='coinbook-{strategy}-position-*'.format(
                        strategy=self.strategy_name))

        return all_positions

    def get_funds(self):
        """Get the details of the current funds held by the user
        returned in units of BTC
        """

        funds_data = json.loads(self.redis.get(
                                'coinbook-{strategy}-funds'.format(
                                    strategy=self.strategy_name)))

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
        self.redis.set(
            'coinbook-{strategy}-funds'.format(
                strategy=self.strategy_name),
            json.dumps(funds_data))

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
            ticker_data = self.bittrex_11_client.get_ticker(ticker)
            exchange_rate = ticker_data.get('result', {}).get('Last')
            if not exchange_rate:
                raise ValueError('Invalid Exchange Rate')
            return amount / exchange_rate

        else:
            # The Target currency is BTC
            ticker = 'BTC-{source}'.format(source=source_currency)
            ticker_data = self.bittrex_11_client.get_ticker(ticker)
            exchange_rate = ticker_data.get('result', {}).get('Last')
            if not exchange_rate:
                raise ValueError('Invalid Exchange Rate')
            return amount * exchange_rate

    def crawl(self):
        """Crawl the market to look for buying opportunities
        """

        summaries = self.bittrex_20_client.get_market_summaries()
        all_coins = summaries.get('result')

        for coin in all_coins:
            trade = self.evaluate_coin(coin)

            if trade:
                self.make_buy(trade=trade)

    def make_buy(self, trade):
        """Make a given trade with the provided parameters
        Updates the amount of funds remaining, and
        creates a new position for the new buy if needed
        :amount is the amount in units of the desired currency
        """

        # Get basic needed elements
        currency = trade.get('currency')
        amount = trade.get('amount')

        # Create the new position
        current_timestamp = datetime.now().isoformat()
        m = hashlib.sha256()
        m.update(currency)
        m.update(current_timestamp)
        pos_hash = m.hexdigest()[:20]
        position_key = 'coinbook-{strategy}-position-{pos_hash}'.format(
                            strategy=self.strategy_name,
                            pos_hash=pos_hash)

        position_data = trade
        position_data.update({"open_timestamp": current_timestamp})

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
            the dictionary should include at least these keys:
            * "currency" - the currency code
            * "amount" - the amount in units of the currency
            In addition, you can include anything that you want
            to use later on during evaluation of the position
        """

        raise NotImplementedError('This should be implemented with the '
                                  'specific strategy you want to test')

    def evaluate_all_positions(self):
        """Evaluate all current positions to check if
        they should be held or closed out
        """

        all_positions = self.get_positions()

        for position in all_positions:
            position_data = json.loads(self.redis.get(position))
            self.evaluate_position(position_data)

    def evaluate_position(self, position):
        """Evaluate a single position currently held.
        The position value passed in is the redis key
        to get the position details
        """

        raise NotImplementedError('This should be implemented with the '
                                  'specific strategy you want to test')

    def get_total_balance(self):
        """Gets the total account balance across
        all held positions and funds
        Returns an answer in units of BTC
        """

        # Get funds balance
        funds_balance = self.get_funds()

        # Get positions balance
        all_positions = self.get_positions()

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

    def write_log(self, message):
        """Write something to the log file for this strategy
        """

        full_log_message = '{timestamp} - {message}'.format(
            timestamp=datetime.now().isoformat(),
            message=message)

        log_file = 'logs/{strategy}.log'.format(strategy=self.strategy_name)
        with open(log_file, 'w+') as log_file_object:
            log_file_object.write(full_log_message)




