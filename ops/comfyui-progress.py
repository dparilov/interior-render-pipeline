#!/usr/bin/env python3
"""Monitor ComfyUI progress via WebSocket"""
import asyncio
import json
import websockets

async def monitor():
    uri = "ws://127.0.0.1:8188/ws"
    async with websockets.connect(uri) as ws:
        print("Connected to ComfyUI WebSocket")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            msg_type = data.get('type')
            
            if msg_type == 'progress':
                val = data['data']['value']
                max_val = data['data']['max']
                pct = (val / max_val) * 100
                print(f"Step {val}/{max_val} ({pct:.0f}%)")
            elif msg_type == 'executing':
                node = data['data'].get('node')
                if node:
                    print(f"Executing: {node}")
            elif msg_type == 'executed':
                print(f"Completed: {data['data'].get('node')}")

asyncio.run(monitor())
