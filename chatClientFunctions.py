import socket
import msgpack
import random
import threading
import time
import socket
import base64
import encryption_manager
import customtkinter as ctk

class ChatClient:
    def __init__(self):
        # Client-Server Connection and Thread Initiation
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect(('csc4026z.link', 51820))
        
        server_public_key = b'f,^\xc0Cb\xf3\x937\xbf\x11\x14"\xed\x13\x0b\x9f\xe7\xaf;\x94\xb0p\x13\xe1\x94\xdd\x85\xcf\x01\x0bC'
        private_key =  base64.b64decode("2PmJnn14IPzuc2REgzUzs4YScgx3SuoA2rwp1TPV9Fc=")

        # encyption_manager init handles all encryption establishing proccesses
        self.manager = encryption_manager.EncryptionManager(server_public_key, private_key, self.sock) 

        # Initial connection request to the server
        packet = msgpack.packb({'request_type':1, 'request_handle': random.randint(0, 2**32 - 1)})
        self.sock.send(self.manager.encrypt(packet))
        
        # Server respond with session id, which is stored globally
        data, _ = self.sock.recvfrom(4096)
        plaintext = self.manager.decrypt(data)
        self.session = msgpack.unpackb(plaintext)['session']
        self.welcome_message = msgpack.unpackb(plaintext) # Welcome message from CONNECT response, passed to chatClientGUI

        self.running = True # False when /DISCONNECT is called
        self.ping_thread = threading.Thread(target=self.ping, daemon=True) # Thread that send a PING every 30 seconds
        self.ping_thread.start()
    
    # Method that handles all user requests
    # User input is split into the command and arguments
    def request(self, userInput):
        split = userInput.split(" ", maxsplit = 2)
        requestType = split[0]
        packet = {}

        try:
            if requestType == "/SET_USERNAME":
                if len(split) < 2:
                    print("[ERROR] /SET_USERNAME requires a username argument")
                    return
                username = split[1]
                packet = {
                    'request_type': 13,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'username': username
                }
            elif requestType == "/USER_LIST":
                if len(split) < 2:
                    print("[ERROR] /USER_LIST requires an offset argument (e.g., /USER_LIST 0)")
                    return
                offset = split[1]
                packet = {
                    'request_type': 14,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'offset': int(offset)
                }
            elif requestType == "/DISCONNECT":
                packet = {
                    'request_type': 2,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1)
                }
                self.running = False
            elif requestType == "/WHOAMI":
                packet = {
                    'request_type': 11,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1)
                }
            elif requestType == "/USER_MESSAGE":  # /USER_MESSAGE <to_username> <message>
                if len(split) < 3:
                    print("[ERROR] /USER_MESSAGE requires a to_username and message argument")
                    return
                to_username = split[1]
                message = split[2]
                packet = {
                    'request_type': 12,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'to_username': to_username,
                    'message': message
                }
            elif requestType == "/WHOIS":
                if len(split) < 2:
                    print("[ERROR] /WHOIS requires a username argument")
                    return
                username = split[1]
                packet = {
                    'request_type': 10,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'username': username
                }
            elif requestType == "/CHANNEL_CREATE":
                if len(split) < 3:
                    print("[ERROR] /CHANNEL_CREATE requires a channel and description argument")
                    return
                channel = split[1]
                description = split[2]
                packet = {
                    'request_type': 4,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'channel': channel,
                    'description': description
                }
            elif requestType == "/CHANNEL_LIST":
                offset = split[1]
                packet = {
                    'request_type': 5,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'offset': int(offset)
                }
            elif requestType == "/CHANNEL_INFO":
                if len(split) < 2:
                    print("[ERROR] /CHANNEL_INFO requires a channel argument")
                    return
                channel = split[1]
                packet = {
                    'request_type': 6,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'channel': channel
                }
            elif requestType == "/CHANNEL_JOIN":
                if len(split) < 2:
                    print("[ERROR] /CHANNEL_JOIN requires a channel argument")
                    return
                channel = split[1]
                packet = {
                    'request_type': 7,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'channel': channel
                }
            elif requestType == "/CHANNEL_LEAVE":
                if len(split) < 2:
                    print("[ERROR] /CHANNEL_LEAVE requires a channel argument")
                    return
                channel = split[1]
                packet = {
                    'request_type': 8,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'channel': channel
                }
            elif requestType == "/CHANNEL_MESSAGE":
                if len(split) < 3:
                    print("[ERROR] /CHANNEL_MESSAGE requires a channel and message argument")
                    return
                channel = split[1]
                message = split[2]
                packet = {
                    'request_type': 9,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1),
                    'channel': channel,
                    'message': message
                }

            if packet:
                encrypted_packet = self.manager.encrypt(msgpack.packb(packet))
                self.sock.send(encrypted_packet)

        except IndexError:
            print(f"[ERROR] Missing argument(s) for command: {requestType}")
        except Exception as e:
            print(f"[ERROR] Failed to build/send request: {e}")

    # Ping method to keep session alive by sending a PING message to the server every 30
    # Method is killed when /DISCONNECT is called
    def ping(self):
        while self.running:
            try:
                packet = {
                    'request_type': 3,
                    'session': self.session,
                    'request_handle': random.randint(0, 2**32 - 1)
                }
                self.sock.send(self.manager.encrypt(msgpack.packb(packet)))
            except Exception as e:
                print(f"Ping failed: {e}")
                # Optional: break or set self.running = False if needed
            time.sleep(30)
