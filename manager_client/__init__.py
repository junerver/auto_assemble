"""
Manager Client Module

This module provides a client for managing notifications and other events
from the webhook server.
"""

from .client import EventManager
from .config import SERVER_HOST_URL, RECONNECT_INTERVAL
from .notifications import show_toast

__version__ = "0.3.1"
__author__ = "Junerver"
__email__ = "junerver@gmail.com"

__all__ = ["EventManager", "show_toast", "SERVER_HOST_URL", "RECONNECT_INTERVAL"]
