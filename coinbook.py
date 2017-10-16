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

    def __init__(self, redis_password=None):

        super(CoinBook, self).__init__()

        self.bittrex_client = Bittrex(None, None, api_version=API_V2_0)
        self.redis = redis.StrictRedis(
            host='localhost', port=6379, db=0, password=redis_password)

    def crawl():
        """Crawl the market to look for buying opportunities
        """
        pass

    def evaluate():
        """Evaluate all current positions to check if
        they should be held or closed out
        """
        pass

    def get_total_balance():
        """Gets the total account balance across
        all held positions and funds
        """
        pass
