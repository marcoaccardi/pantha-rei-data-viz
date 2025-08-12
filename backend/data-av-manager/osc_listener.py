#!/usr/bin/env python3
"""
OSC Listener for Max/MSP Integration
Listens on port 7400 for /test_slider messages from Max
"""

from pythonosc import dispatcher
from pythonosc import osc_server
import sys
import time

def temperature_handler(unused_addr, value):
    """Handle /temperature messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Temperature: {value}")

def health_score_handler(unused_addr, value):
    """Handle /health_score messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Health Score: {value}")

def acidification_handler(unused_addr, value):
    """Handle /acidification messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Acidification: {value}")

def oxygen_handler(unused_addr, value):
    """Handle /oxygen messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Oxygen: {value}")

def marine_life_handler(unused_addr, value):
    """Handle /marine_life messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Marine Life: {value}")

def currents_handler(unused_addr, value):
    """Handle /currents messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Currents: {value}")

def threat_level_handler(unused_addr, value):
    """Handle /threat_level messages from Max"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Threat Level: {value}")

def default_handler(address, *args):
    """Handle any other OSC messages"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] Received message: {address} with args: {args}")

def main():
    print("Starting OSC Listener on port 7400...")
    print("Listening for ocean data messages from Max:")
    print("- /temperature")
    print("- /health_score")
    print("- /acidification")
    print("- /oxygen")
    print("- /marine_life")
    print("- /currents")
    print("- /threat_level")
    print("Press Ctrl+C to stop\n")
    
    # Create dispatcher and add handlers
    disp = dispatcher.Dispatcher()
    disp.map("/temperature", temperature_handler)
    disp.map("/health_score", health_score_handler)
    disp.map("/acidification", acidification_handler)
    disp.map("/oxygen", oxygen_handler)
    disp.map("/marine_life", marine_life_handler)
    disp.map("/currents", currents_handler)
    disp.map("/threat_level", threat_level_handler)
    disp.set_default_handler(default_handler)
    
    # Create and start server
    try:
        server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 7400), disp)
        print("OSC Server running on 127.0.0.1:7400")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down OSC Listener...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()