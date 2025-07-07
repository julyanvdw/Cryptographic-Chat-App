#CSC4026Z 
#KAJ networks assignment
#Secure UDP Chatting with KAJ

import customtkinter as ctk
import threading
from threading import Event
import msgpack
from PIL import Image
import datetime

from chatClientFunctions import ChatClient

ctk.set_appearance_mode("Light")  # Start with system theme

class ChatClientGUI:
    def __init__(self):
        #Window
        self.root = ctk.CTk()
        self.root.title("Secure UDP Chatting with KAJ")
        self.root.geometry("1280x720")

        #Create the ChatClient instance
        self.client = ChatClient()         
        self.user_offset = 0
        self.channel_offset = 0
        self.cached_users = []
        self.cached_channels = []
        self.current_channel = None  
        self.current_username = None  

        #Top pane: Logo, title, username entry, dark mode toggle 
        top = ctk.CTkFrame(self.root)
        top.pack(side="top", fill="x", padx=10, pady=(10,0))
        try:
            logo_img = ctk.CTkImage(Image.open("KAJ_Logo.png"), size=(40, 40)) #Logo image
            logo_label = ctk.CTkLabel(top, image=logo_img, text="")
            logo_label.pack(side="left", padx=(0, 10))
        except Exception as e:
            print(f"Could not load logo image: {e}")
        app_title = ctk.CTkLabel(top, text="Secure UDP Chatting with KAJ", font=(None, 14, "bold")) #    Title label
        app_title.pack(side="left", padx=(0, 10))

        self.mode_var = ctk.StringVar(value="Light")
        mode_toggle = ctk.CTkSwitch(
            top,
            text="Dark Mode",
            variable=self.mode_var,
            onvalue="Dark",
            offvalue="Light",
            command=self.toggle_mode
        )
        mode_toggle.pack(side="right", padx=10)

        self.username_entry = ctk.CTkEntry(top, placeholder_text="Enter new username…")
        self.username_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        ctk.CTkButton(top, text="Set Username", command=self.set_username).pack(side="left")

        #Left pane: Users list & pagination
        self.left = ctk.CTkFrame(self.root, width=200)
        self.left.pack(side="left", fill="y", padx=(10,5), pady=10)
        ctk.CTkLabel(self.left, text="Users", font=(None,14,"bold")).pack(pady=(5,2))
        self.user_box = ctk.CTkTextbox(self.left, width=200, height=400)
        self.user_box.pack()
        self.user_box.configure(state="disabled")
        self.user_box.bind("<Button-1>", self.on_user_click)
        ctk.CTkButton(self.left, text="Refresh Users", command=self.fetch_users).pack(pady=(2,2))
        ctk.CTkButton(self.left, text="Previous Users", command=self.prev_users).pack(pady=(2,2))
        ctk.CTkButton(self.left, text="Next Users", command=self.next_users).pack(pady=(0,5))
        # Connect/Disconnect toggle button
        self.connected = True
        def _toggle_connection():
            if self.connected:
                # Disconnect
                self.client.request("/DISCONNECT")
                self.client.sock.close()
                self.connected = False
                self.conn_button.configure(text="CONNECT", fg_color="green")
                self.show_info("[{0}] 🔌 Disconnected from server.".format(datetime.datetime.now().strftime("%H:%M:%S")))
            else:
                # Reconnect
                self.reconnect()
                self.connected = True
                self.conn_button.configure(text="DISCONNECT", fg_color="red")
        self.conn_button = ctk.CTkButton(
            self.left,
            text="DISCONNECT",
            fg_color="red",
            command=_toggle_connection
        )
        self.conn_button.pack(side="bottom", pady=(5,5))

        #Right pane: Channels list & pagination
        self.right = ctk.CTkFrame(self.root, width=200)
        self.right.pack(side="right", fill="y", padx=(5,10), pady=10)
        ctk.CTkLabel(self.right, text="Channels", font=(None,14,"bold")).pack(pady=(5,2))
        self.channel_box = ctk.CTkTextbox(self.right, width=180, height=250)
        self.channel_box.pack()
        self.channel_box.configure(state="disabled")
        ctk.CTkButton(self.right, text="Refresh Channels", command=self.fetch_channels).pack(pady=(2,2))
        ctk.CTkButton(self.right, text="Previous Channels", command=self.prev_channels).pack(pady=(2,2))
        ctk.CTkButton(self.right, text="Next Channels", command=self.next_channels).pack(pady=(0,5))
        # Add select/join channel
        self.join_channel_entry = ctk.CTkEntry(self.right, placeholder_text="Channel to join")
        self.join_channel_entry.pack(pady=(5,2))
        ctk.CTkButton(self.right, text="Join Channel", command=self.join_channel).pack(pady=(2,5))
        ctk.CTkButton(self.right, text="Leave Channel", command=self.leave_channel).pack(pady=(2,5))
        #Channel creation controls
        ctk.CTkLabel(self.right, text="Create New Channel", font=(None,12,"bold")).pack(pady=(10,2))
        self.create_channel_entry = ctk.CTkEntry(self.right, placeholder_text="New channel name")
        self.create_channel_entry.pack(pady=(2,2))
        self.create_channel_desc_entry = ctk.CTkEntry(self.right, placeholder_text="Channel description")
        self.create_channel_desc_entry.pack(pady=(2,2))
        ctk.CTkButton(self.right, text="Create Channel", command=self.create_channel).pack(pady=(2,5))

        #Center pane: Chat area + input
        center = ctk.CTkFrame(self.root)
        center.pack(side="left", expand=True, fill="both", padx=5, pady=10)

        self.chat_box = ctk.CTkTextbox(center)
        self.chat_box.pack(expand=True, fill="both")
        self.chat_box.configure(state="disabled")

        # Show server welcome message
        self.chat_box.configure(state="normal")
        welcome = getattr(self.client, 'welcome_message', {}).get('message', '')
        if welcome:
            self.chat_box.insert("end", welcome + "\n")
        self.chat_box.configure(state="disabled")

        # Show the current username immediately -> WHY WAS I DOING THIS?
        #self.client.request("/WHOAMI")

        input_row = ctk.CTkFrame(center)
        input_row.pack(fill="x", pady=(5,0))
        self.input_entry = ctk.CTkEntry(input_row, placeholder_text="Type message…")
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.bind("<Tab>", self.autocomplete)
        self.input_entry.bind("<Return>", lambda event: self.send_message())
        ctk.CTkButton(input_row, text="Send", command=self.send_message).pack(side="left", padx=(5,0))
        ctk.CTkButton(input_row, text="Clear Chat", command=self.clear_chat).pack(side="left", padx=(5,0))
        ctk.CTkButton(input_row, text="Help", command=self.show_help).pack(side="left", padx=(5,0))

        #Initial population of users and channels
        self.fetch_users()
        self.fetch_channels()

        # Create a flag to stop the listener
        self._stop_event = threading.Event()
        self.listener_thread = threading.Thread(
            target=self.listen_for_messages,
            daemon=True
        )
        self.listener_thread.start()

        # Start the main loop
        self.root.mainloop()

    # Methods for user actions
    def set_username(self):
        new_name = self.username_entry.get().strip()
        if not new_name:
            self.show_info("Error: Missing or invalid arguments for command /SET_USERNAME")
            return
        self.client.request(f"/SET_USERNAME {new_name}")
        self.username_entry.delete(0, 'end')
    # Fetch users 
    def fetch_users(self):
        offset = self.user_offset
        if not isinstance(offset, int) or offset < 0:
            offset = 0
            self.user_offset = 0
        self.client.request(f"/USER_LIST {offset}")
    # Fetch channels
    def fetch_channels(self):
        offset = self.channel_offset
        if not isinstance(offset, int) or offset < 0:
            offset = 0
            self.channel_offset = 0
        self.client.request(f"/CHANNEL_LIST {offset}")
    # Update the user and channel lists in the GUI
    def update_user_list(self):
        display_list = list(self.cached_users)
        self.user_box.configure(state="normal")
        self.user_box.delete("1.0", "end")
        for u in display_list:
            label = u
            if self.current_username and u == self.current_username:
                label = f"{u} 👈 (You)"
            self.user_box.insert("end", label + "\n")
        self.user_box.configure(state="disabled")
    # Update the channel list in the GUI
    def update_channel_list(self):
        self.channel_box.configure(state="normal")
        self.channel_box.delete("1.0", "end")
        for ch in self.cached_channels:
            self.channel_box.insert("end", ch + "\n")
        self.channel_box.configure(state="disabled")
    # Pagination methods for users and channels
    def prev_users(self):
        if self.user_offset >= 20:
            self.user_offset -= 20
        else:
            self.user_offset = 0
        self.fetch_users()

    def next_users(self):
        self.user_offset += 20
        self.fetch_users()

    def prev_channels(self):
        if self.channel_offset >= 10:
            self.channel_offset -= 10
        else:
            self.channel_offset = 0
        self.fetch_channels()

    def next_channels(self):
        self.channel_offset += 10
        self.fetch_channels()
    # Join a channel
    def join_channel(self):
        channel = self.join_channel_entry.get().strip()
        if not channel:
            self.show_info("Error: Missing or invalid arguments for command /CHANNEL_JOIN")
            return
        self.client.request(f"/CHANNEL_JOIN {channel}")
        self.current_channel = channel
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"[{now}] ⏳ Attempting to join channel: {channel} ...\n")
        self.chat_box.configure(state="disabled")

    def send_message(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        now = datetime.datetime.now().strftime("%H:%M:%S")
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if command == "/HELP":
                self.show_help()
                self.input_entry.delete(0, 'end')
                return
            elif command == "/USER_LIST":
                offset_str = args.strip()
                if offset_str == "":
                    offset = 0
                else:
                    try:
                        offset = int(offset_str)
                        if offset < 0:
                            raise ValueError()
                    except ValueError:
                        self.show_info("Error: Missing or invalid arguments for command /USER_LIST")
                        return
                self.client.request(f"/USER_LIST {offset}")
            elif command == "/CHANNEL_LIST":
                offset_str = args.strip()
                if offset_str == "":
                    offset = 0
                else:
                    try:
                        offset = int(offset_str)
                        if offset < 0:
                            raise ValueError()
                    except ValueError:
                        self.show_info("Error: Missing or invalid arguments for command /USER_LIST")
                        return
                self.client.request(f"/CHANNEL_LIST {offset}")
            elif command == "/CHANNEL_MESSAGE":
                if not args:
                    self.show_info("Error: Missing or invalid arguments for command /CHANNEL_MESSAGE")
                    return
                args_parts = args.split(maxsplit=1)
                if len(args_parts) < 2:
                    self.show_info("Error: Missing or invalid arguments for command /CHANNEL_MESSAGE")
                    return
                channel, message = args_parts[0], args_parts[1]
                if not channel or not message:
                    self.show_info("Error: Missing or invalid arguments for command /CHANNEL_MESSAGE")
                    return
                self.client.request(f"/CHANNEL_MESSAGE {channel} {message}")
                # Format: [HH:MM:SS] ➡️ YOU in #channel: message
                self.chat_box.configure(state="normal")
                self.chat_box.insert("end", f"[{now}] ➡️ YOU in #{channel}: {message}\n")
                self.chat_box.configure(state="disabled")

            elif command == "/USER_MESSAGE":
                if not args:
                    self.show_info("Error: Missing arguments for /USER_MESSAGE")
                    return
                args_parts = args.split(maxsplit=1)
                if len(args_parts) < 2:
                    self.show_info("Error: Missing message for /USER_MESSAGE")
                    return
                to_user, message = args_parts[0], args_parts[1].strip()
                if not to_user or not message:
                    self.show_info("Error: Missing user or message for /USER_MESSAGE")
                    return
                self.client.request(f"/USER_MESSAGE {to_user} {message}")
                self.chat_box.configure(state="normal")
                self.chat_box.insert("end", f"[{now}] ➡️ YOU (to {to_user}): {message}\n")
                self.chat_box.configure(state="disabled")

            elif command == "/WHOIS":
                username = args.strip()
                if not username:
                    self.show_info("Error: Missing or invalid arguments for command /WHOIS")
                    return
                self.client.request(f"/WHOIS {username}")
            elif command == "/CHANNEL_INFO":
                channel = args.strip()
                if not channel:
                    self.show_info("Error: Missing or invalid arguments for command /CHANNEL_INFO")
                    return
                self.client.request(f"/CHANNEL_INFO {channel}")
            else:
                self.client.request(text)
        else:
            if not self.current_channel:
                self.show_info("Join a channel first!")
                return
            self.client.request(f"/CHANNEL_MESSAGE {self.current_channel} {text}")
            # Format: [HH:MM:SS] ➡️ YOU in #channel: message
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"[{now}] ➡️ YOU in #{self.current_channel}: {text}\n")
            self.chat_box.configure(state="disabled")
        self.input_entry.delete(0, 'end')

    def create_channel(self):
        name = self.create_channel_entry.get().strip()
        desc = self.create_channel_desc_entry.get().strip()
        if not name or not desc:
            self.show_info("Error: Both channel name and description are required to create a channel.")
            return
        self.show_info(f"Attempting to create channel: {name} ...")
        self.client.request(f"/CHANNEL_CREATE {name} {desc}")
        self.create_channel_entry.delete(0, 'end')
        self.create_channel_desc_entry.delete(0, 'end')
        # Update the channel list after a short delay
        self.root.after(500, self.fetch_channels)
        # Automatically join the new channel after short delay (to allow creation)
        def join_created_channel():
            self.client.request(f"/CHANNEL_JOIN {name}")
            self.current_channel = name
            self.show_info(f"✅ Channel '{name}' created successfully!\n🔗 Automatically joined new channel: {name}")
        self.root.after(800, join_created_channel)

    # Autocomplete functionality for input entry
    def autocomplete(self, event):
        commands = [
            "/SET_USERNAME ",
            "/USER_LIST ",
            "/CHANNEL_LIST ",
            "/CHANNEL_JOIN ",
            "/CHANNEL_LEAVE ",
            "/CHANNEL_CREATE ",
            "/CHANNEL_INFO ",
            "/CHANNEL_MESSAGE ",
            "/USER_MESSAGE ",
            "/WHOAMI",
            "/WHOIS ",
            "/DISCONNECT",
            "/HELP"
        ]
        txt = self.input_entry.get()
        matches = [c for c in commands if c.startswith(txt)]
        if matches:
            self.input_entry.delete(0, 'end')
            self.input_entry.insert(0, matches[0])
        return "break"
    
    # Background listener for incoming messages
    # This runs in a separate thread to avoid blocking the GUI
    def listen_for_messages(self):
        import datetime
        while not self._stop_event.is_set():
            try:
                data, _ = self.client.sock.recvfrom(4096)
                plaintext = self.client.manager.decrypt(data)
                msg = msgpack.unpackb(plaintext, raw=False)
                print(msg)
                now = datetime.datetime.now().strftime("%H:%M:%S")
                display = None
                if isinstance(msg, dict):
                    rt = msg.get('response_type')
                    # 30: CHANNEL_MESSAGE_response
                    if rt == 30:
                        channel = msg.get('channel', '<unknown>')
                        username = msg.get('username', '<unknown>')
                        message = msg.get('message', '')
                        sender = "YOU" if username == self.current_username else username
                        display = f"[{now}] #{channel} | {sender}: {message}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 27: CHANNEL_INFO_response
                    elif rt == 27:
                        channel = msg.get('channel', '<unknown>')
                        desc = msg.get('description', '')
                        members = msg.get('members', [])
                        display = (
                            f"📃 Channel Info\n"
                            f"Name: {channel}\n"
                            f"Description: {desc}\n"
                            f"Members ({len(members)}): {', '.join(str(m) for m in members)}"
                        )
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 33: USER_MESSAGE_response (direct message)
                    elif rt == 33:
                        username = msg.get('from_username', '<unknown>')
                        message = msg.get('message', '')
                        sender = "YOU" if username == self.current_username else username
                        display = f"[{now}] DM from {sender}: {message}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 31: WHOIS_response
                    elif rt == 31:
                        username = msg.get('username', 'N/A')
                        status = msg.get('status', 'N/A')
                        transport = msg.get('transport', 'N/A')
                        wg_pubkey = msg.get('wireguard_public_key', 'N/A')
                        channels = msg.get('channels', [])
                        if not isinstance(channels, list):
                            channels = []
                        channels_str = ', '.join(str(ch) for ch in channels) if channels else 'N/A'
                        display = (
                            "---\n"
                            "🔍 User Info\n"
                            f"Username: {username}\n"
                            f"Status: {status}\n"
                            f"Transport: {transport}\n"
                            f"Wireguard Public Key: {wg_pubkey}\n"
                            f"Channels: {channels_str}\n"
                            "---"
                        )
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 25: CHANNEL_CREATE_response
                    elif rt == 25:
                        channel = msg.get('channel', '<unknown>')
                        display = f"[{now}] ✅ Channel '{channel}' created (and joined)"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 26: CHANNEL_LIST_response
                    elif rt == 26:
                        channels = msg.get('channels', [])
                        self.cached_channels = channels
                        self.update_channel_list()
                        continue
                    # 35: USER_LIST_response
                    elif rt == 35:
                        users = msg.get('users', [])
                        self.cached_users = users
                        self.update_user_list()
                        continue
                    # 28: CHANNEL_JOIN_response
                    elif rt == 28:
                        channel = msg.get('channel', '<unknown>')
                        display = f"[{now}] ✅ Successfully joined channel: {channel}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 29: CHANNEL_LEFT_response
                    elif rt == 29:
                        channel = msg.get('channel', '<unknown>')
                        display = f"[{now}] ℹ️ Left channel: {channel}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 34: SET_USERNAME_response
                    elif rt == 34:
                        old = msg.get('old_username', '<unknown>')
                        new = msg.get('new_username', '<unknown>')
                        self.current_username = new
                        self.client.request("/WHOAMI")
                        self.fetch_users()
                        display = f"📝 Username changed!\n Old Username: {old}\nNew Username: {new}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 20: ERROR_response
                    elif rt == 20:
                        err = msg.get('error', 'Unknown error')
                        context = ""
                        if 'join' in err.lower():
                            context = "Channel join error"
                        elif 'create' in err.lower():
                            context = "Channel creation error"
                        elif 'leave' in err.lower():
                            context = "Channel leave error"
                        elif "not found" in err.lower():
                            if "channel" in err.lower():
                                context = "Channel error"
                            elif "user" in err.lower() or "username" in err.lower():
                                context = "User error"
                        if context:
                            display = f"[{now}] ❗ {context}: {err}"
                        else:
                            display = f"[{now}] ❗ {err}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 21: OK_response
                    elif rt == 21:
                        display = f"[{now}] ✅ Request processed successfully."
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 24: PING_response
                    elif rt == 24:
                        # Optionally suppress, or show for debug:
                        display = f"[{now}] 🔄 Ping received from server"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 36: SERVER_MESSAGE_response
                    elif rt == 36:
                        message = msg.get('message', '')
                        display = f"[{now}] 📢 Server: {message}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 37: SERVER_SHUTDOWN_response
                    elif rt == 37:
                        message = msg.get('message', '')
                        display = f"[{now}] ⚠️ Server shutdown: {message}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 32: WHOAMI_response
                    elif rt == 32:
                        username = msg.get('username', None)
                        if username is not None:
                            self.current_username = username
                        display = f"[{now}] Username: {username}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # 23: DISCONNECT_response
                    elif rt == 23:
                        message = msg.get('message', '')
                        display = f"[{now}] 🔌 Disconnected: {message}"
                        self.chat_box.configure(state="normal")
                        self.chat_box.insert("end", display + "\n")
                        self.chat_box.configure(state="disabled")
                        continue
                    # Fallback for unknown response_type
                    else:
                        display = str(msg)
                else:
                    display = str(msg)
                if display is not None:
                    self.chat_box.configure(state="normal")
                    self.chat_box.insert("end", display + "\n")
                    self.chat_box.configure(state="disabled")
            except OSError:
                # Socket closed, exit listener cleanly
                break
            except Exception as e:
                self.show_info(f"Listener error: {e}")

    def on_user_click(self, event):
        # Get the clicked line in the user_box and prefill input_entry with /USER_MESSAGE <username>
        try:
            index = self.user_box.index(f"@{event.x},{event.y}")
            line = int(index.split('.')[0])
            # Get the content of the clicked line
            user_line = self.user_box.get(f"{line}.0", f"{line}.end").strip()
            # Remove label if it's current user
            if user_line.endswith("👈 (You)"):
                username = user_line.split("👈")[0].strip()
            else:
                username = user_line
            # Only prefill if not empty and not the current user
            if username and (not self.current_username or username != self.current_username):
                self.input_entry.delete(0, 'end')
                self.input_entry.insert(0, f"/USER_MESSAGE {username} ")
        except Exception as e:
            pass

    def show_info(self, info):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{info}\n")
        self.chat_box.configure(state="disabled")
    def toggle_mode(self):
        new_mode = self.mode_var.get()
        ctk.set_appearance_mode(new_mode)

    def show_help(self):
        help_text = (
            """
📖 Available Commands

/SET_USERNAME <new_name>           – Change your username
/USER_LIST <offset>                – List users (for pagination)
/CHANNEL_LIST <offset>             – List channels (for pagination)
/CHANNEL_JOIN <name>               – Join a channel
/CHANNEL_LEAVE <name>              – Leave a channel
/CHANNEL_CREATE <name> <desc>      – Create a channel
/CHANNEL_MESSAGE <channel> <msg>   – Send message to channel
/USER_MESSAGE <username> <msg>     – Send a private message to user
/WHOAMI                            – Show your username
/WHOIS <username>                  – Get info about a user
/DISCONNECT                        – Disconnect from server
/HELP                              – Show this help message

Examples:
  /SET_USERNAME Alice
  /USER_LIST 20
  /CHANNEL_MESSAGE general Hello everyone!
  /USER_MESSAGE Bob Hi Bob!

Note: Offsets are used for pagination. Use /HELP any time to show this message.
"""
        )
        self.show_info(help_text)

    def reconnect(self):
        """Tear down and rebuild the entire client exactly as on startup."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            #stop the existing listener
            self._stop_event.set()
            try:
                self.listener_thread.join(timeout=1)
            except:
                pass
            #cleanly shut down existing client
            try:
                self.client.request("/DISCONNECT")
                self.client.sock.close()
            except:
                pass

            # re-create and re-initialize ChatClient (runs CONNECT handshake)
            self.client = ChatClient()

            #reset GUI state
            self.current_channel = None
            self.current_username = None
            self.user_offset = 0
            self.channel_offset = 0
            self.cached_users.clear()
            self.cached_channels.clear()
            self.chat_box.configure(state="normal")
            self.chat_box.delete("1.0", "end")
            self.chat_box.configure(state="disabled")

            # fetch fresh lists and WHOAMI to repopulate state
            self.client.request("/WHOAMI")
            self.fetch_users()
            self.fetch_channels()

            #restart listener on new socket
            self._stop_event.clear()
            self.listener_thread = threading.Thread(
                target=self.listen_for_messages,
                daemon=True
            )
            self.listener_thread.start()

            # 7) Notify user
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"[{now}] 🔄 Reconnected to server.\n")
            self.chat_box.configure(state="disabled")

        except Exception as e:
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", f"[{now}] ❗ Reconnect failed: {e}\n")
            self.chat_box.configure(state="disabled")

    # Clear chat area
    def clear_chat(self):
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        
    # ChatClientGUI class to handle the GUI
    def leave_channel(self):
        if self.current_channel:
            self.client.request(f"/CHANNEL_LEAVE {self.current_channel}")
            self.show_info(f"ℹ️ Leaving channel: {self.current_channel}")
            self.current_channel = None
        else:
            self.show_info("⚠️ You are not currently in any channel.")

if __name__ == "__main__":
    ChatClientGUI()
