"""
Manager Client Module

This module provides a client for managing notifications and other events
from the webhook server.
"""

from manager_client.client import EventManager
from manager_client.config import SERVER_HOST_URL, RECONNECT_INTERVAL
from manager_client.notifications import show_toast

__author__ = "Junerver"
__email__ = "junerver@gmail.com"

__all__ = ["EventManager", "show_toast", "SERVER_HOST_URL", "RECONNECT_INTERVAL"]
