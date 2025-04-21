"""
Notifications Module

This module provides toast notification functionality for Windows.
"""

import asyncio
import logging
import sys
import threading

try:
    from win11toast import toast
except ImportError:
    toast = None


def show_toast(title: str, message: str):
    """显示 Windows 通知"""
    if sys.platform != "win32":
        logging.info(f"Toast notification: {title} - {message}")
        return

    if toast is None:
        logging.error("win11toast module not found")
        return

    def run_toast():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            toast(title, message)
            loop.close()
        except Exception as e:
            logging.error(f"Error showing toast: {e}")

    thread = threading.Thread(target=run_toast)
    thread.start()
