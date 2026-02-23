# services/video_service.py
import json
import time
import threading
import uuid
from flask_sock import Sock

class VideoService:
    def __init__(self):
        # WebSocket connections storage
        self.hr_sockets = {}
        self.user_sockets = {}
        self.pending_offers = {}
        self.pending_answers = {}
        self.pending_ice = {}
        self.pending_ice_hr = {}
    
    def create_jitsi_meeting(self):
        """Generates a unique Jitsi URL as a fallback."""
        unique_room_name = f"Interview-{uuid.uuid4().hex[:12]}"
        return f"https://meet.jit.si/{unique_room_name}"
    
    def trigger_fallback(self, app_id):
        """Notifies both parties to redirect to the internal fallback page."""
        # This generates the URL for your internal Flask route
        internal_url = f"/video-fallback/{app_id}" 
        
        fallback_msg = json.dumps({
            "type": "fallback", 
            "url": internal_url
        })
        
        # Notify both HR and User
        for sockets in [self.hr_sockets, self.user_sockets]:
            if app_id in sockets:
                try:
                    sockets[app_id].send(fallback_msg)
                except Exception:
                    print(f"[VideoService] Error sending fallback to {app_id},{Exception}")
                    pass

    def ws_keepalive(self, ws, interval=20):
        """Send ping messages to keep WebSocket alive."""
        try:
            while True:
                ws.send(json.dumps({"type": "ping"}))
                time.sleep(interval)
        except Exception:
            pass
    
    def handle_hr_connection(self, ws, app_id):
        """Handle HR WebSocket connection"""
        print(f"[VideoService] HR WebSocket connected for app_id: {app_id}")
        self.hr_sockets[app_id] = ws
        
        # Start keepalive thread
        threading.Thread(target=self.ws_keepalive, args=(ws,), daemon=True).start()
        
        # Notify candidate HR is online
        if app_id in self.user_sockets:
            try:
                self.user_sockets[app_id].send(json.dumps({"type": "hr_online"}))
                print(f"[VideoService] Notified user {app_id} that HR is online")
            except Exception as e:
                print(f"[VideoService] Error notifying user: {e}")
        else:
            print(f"[VideoService] User not connected yet for app_id: {app_id}")
        
        # Send all buffered ICE from user to HR
        if app_id in self.pending_ice_hr:
            print(f"[VideoService] Sending {len(self.pending_ice_hr[app_id])} buffered ICE candidates to HR {app_id}")
            for c in self.pending_ice_hr[app_id]:
                try:
                    ws.send(json.dumps({"type": "ice", "ice": c}))
                except Exception as e:
                    print(f"[VideoService] Error sending buffered ICE to HR: {e}")
        
        try:
            while True:
                msg = ws.receive()
                if not msg:
                    print(f"[VideoService] HR WebSocket closed for app_id: {app_id}")
                    break
                
                print(f"[VideoService] HR received message for app_id {app_id}: {msg[:100]}...")
                data = json.loads(msg)
                
                # HR SENDS OFFER
                if data["type"] == "offer":
                    print(f"[VideoService] HR sending offer to user for app_id: {app_id}")
                    if app_id in self.user_sockets:
                        self.user_sockets[app_id].send(json.dumps({
                            "type": "offer",
                            "offer": data["offer"]
                        }))
                        print(f"[VideoService] Offer forwarded to user {app_id}")
                    else:
                        self.pending_offers[app_id] = data["offer"]
                        print(f"[VideoService] Offer stored pending user connection for app_id: {app_id}")
                
                # HR ICE
                elif data["type"] == "ice":
                    # Always buffer ICE
                    self.pending_ice.setdefault(app_id, []).append(data["ice"])
                    # Relay ICE to user if connected
                    if app_id in self.user_sockets:
                        try:
                            self.user_sockets[app_id].send(json.dumps({
                                "type": "ice",
                                "ice": data["ice"]
                            }))
                        except Exception as e:
                            print(f"[VideoService] Error sending ICE to user: {e}")
                # Handle pings/pongs
                elif data["type"] == "ping":
                    continue
        except Exception as e:
            print(f"[VideoService] HR WebSocket error for app_id {app_id}: {e}")
        finally:
            self.hr_sockets.pop(app_id, None)
            print(f"[VideoService] HR WebSocket cleaned up for app_id: {app_id}")
    
    def handle_user_connection(self, ws, app_id):
        """Handle User WebSocket connection"""
        print(f"[VideoService] USER WebSocket connected for app_id: {app_id}")
        self.user_sockets[app_id] = ws
        
        # Start keepalive thread
        threading.Thread(target=self.ws_keepalive, args=(ws,), daemon=True).start()
        
        # Send pending events if user came late
        if app_id in self.pending_offers:
            try:
                ws.send(json.dumps({"type": "offer", "offer": self.pending_offers[app_id]}))
            except Exception as e:
                print(f"[VideoService] Error sending pending offer: {e}")
            del self.pending_offers[app_id]
        
        if app_id in self.pending_ice:
            print(f"[VideoService] Sending {len(self.pending_ice[app_id])} buffered ICE candidates to user {app_id}")
            for c in self.pending_ice[app_id]:
                try:
                    ws.send(json.dumps({"type": "ice", "ice": c}))
                except Exception as e:
                    print(f"[VideoService] Error sending buffered ICE: {e}")
        
        # Notify HR that user joined
        if app_id in self.hr_sockets:
            try:
                self.hr_sockets[app_id].send(json.dumps({"type": "user_online"}))
            except Exception as e:
                print(f"[VideoService] Error notifying HR: {e}")
        
        try:
            while True:
                msg = ws.receive()
                if not msg:
                    print(f"[VideoService] USER WebSocket closed for app_id: {app_id}")
                    break
                
                print(f"[VideoService] USER received message for app_id {app_id}: {msg[:100]}...")
                data = json.loads(msg)
                
                # USER SENDS ANSWER
                if data["type"] == "answer":
                    print(f"[VideoService] User sending answer to HR for app_id: {app_id}")
                    if app_id in self.hr_sockets:
                        self.hr_sockets[app_id].send(json.dumps({
                            "type": "answer",
                            "answer": data["answer"]
                        }))
                        print(f"[VideoService] Answer forwarded to HR {app_id}")
                    else:
                        self.pending_answers[app_id] = data["answer"]
                        print(f"[VideoService] Answer stored pending HR connection for app_id: {app_id}")
                
                # USER ICE
                elif data["type"] == "ice":
                    # Always buffer ICE
                    self.pending_ice_hr.setdefault(app_id, []).append(data["ice"])
                    # Relay ICE to HR if connected
                    if app_id in self.hr_sockets:
                        try:
                            self.hr_sockets[app_id].send(json.dumps({
                                "type": "ice",
                                "ice": data["ice"]
                            }))
                        except Exception as e:
                            print(f"[VideoService] Error sending ICE to HR: {e}")
                elif data["type"] == "ping":
                    continue
        except Exception as e:
            print(f"[VideoService] USER WebSocket error for app_id {app_id}: {e}")
        finally:
            self.user_sockets.pop(app_id, None)
            print(f"[VideoService] USER WebSocket cleaned up for app_id: {app_id}")

# Create singleton instance
video_service = VideoService()