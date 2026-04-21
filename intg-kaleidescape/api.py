"""
Integration API setup for Kaleidescape UC integration.

Initializes the ucapi IntegrationAPI instance and event loop.

:copyright: (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio

import ucapi

loop = asyncio.new_event_loop()
api = ucapi.IntegrationAPI(loop)
