#!/usr/bin/env python3

import os
import time
import json
import pickle
import pyautogui
from pynput import mouse

class MouseRecorder:
    def __init__(self, recording_file="mouse_actions.pkl"):
        self.recording_file = recording_file
        self.actions = []
        self.is_recording = False
        self.listener = None
    
    def on_click(self, x, y, button, pressed):
        """Callback when mouse events occur during recording"""
        if pressed:
            # Store only press events (not release)
            self.actions.append({"type": "click", "x": x, "y": y, "time": time.time()})
            print(f"Recorded click at position ({x}, {y})")
    
    def start_recording(self):
        """Start recording mouse clicks"""
        print("Starting to record mouse actions. Click to record positions.")
        print("Press Ctrl+C in the terminal when finished recording.")
        self.actions = []
        self.is_recording = True
        # Start listening for mouse events
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()
        
        try:
            # Keep recording until keyboard interrupt
            while self.is_recording:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_recording()
    
    def stop_recording(self):
        """Stop the recording process"""
        if self.listener:
            self.listener.stop()
        self.is_recording = False
        print(f"Recording stopped. Recorded {len(self.actions)} actions.")
        
        # Calculate time differences between clicks
        if len(self.actions) > 1:
            prev_time = self.actions[0]["time"]
            for i in range(1, len(self.actions)):
                self.actions[i]["delay"] = self.actions[i]["time"] - prev_time
                prev_time = self.actions[i]["time"]
            self.actions[0]["delay"] = 0  # First action has no delay
        
        # Remove absolute timestamps as they're no longer needed
        for action in self.actions:
            if "time" in action:
                del action["time"]
        
        # Save the recording
        self.save_recording()
    
    def save_recording(self):
        """Save the recorded actions to a file"""
        with open(self.recording_file, 'wb') as f:
            pickle.dump(self.actions, f)
        print(f"Recording saved to {self.recording_file}")
        
        # Also save as readable JSON for debugging
        with open(f"{os.path.splitext(self.recording_file)[0]}.json", 'w') as f:
            json.dump(self.actions, f, indent=2)
    
    def load_recording(self):
        """Load recorded actions from file"""
        try:
            with open(self.recording_file, 'rb') as f:
                self.actions = pickle.load(f)
            print(f"Loaded {len(self.actions)} actions from {self.recording_file}")
            return True
        except FileNotFoundError:
            print(f"Recording file {self.recording_file} not found.")
            return False
    
    def replay(self):
        """Replay the recorded mouse actions"""
        if not self.actions:
            if not self.load_recording():
                print("No actions to replay. Record some actions first.")
                return
        
        print(f"Replaying {len(self.actions)} mouse actions...")
        for i, action in enumerate(self.actions):
            # Wait the recorded delay
            if "delay" in action and i > 0:  # Skip delay for first action
                time.sleep(action["delay"])
            
            # Perform the action
            if action["type"] == "click":
                pyautogui.click(action["x"], action["y"])
                print(f"Clicked at position ({action['x']}, {action['y']})")
        
        print("Replay completed!")


if __name__ == "__main__":
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Record and replay mouse clicks')
    parser.add_argument('action', choices=['record', 'replay'], help='Action to perform')
    parser.add_argument('--name', default='mouse_actions', help='Name for the recording (default: mouse_actions)')
    args = parser.parse_args()
    
    # Create recorder with the specified filename
    recorder = MouseRecorder(f"{args.name}.pkl")
    
    if args.action == 'record':
        # Record mouse actions
        recorder.start_recording()
    else:
        # Replay recorded actions
        recorder.replay()