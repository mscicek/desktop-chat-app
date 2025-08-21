import customtkinter as ctk
import socket
import threading
import time
import protocol
from functools import partial

class ChatClient(ctk.CTk):
    """The main application class for the client GUI."""
    def __init__(self):
        super().__init__()
        self.title("Network Project Chat")
        self.geometry("1100x700")
        ctk.set_appearance_mode("dark")

       
        self.tcp_socket = None
        self.udp_socket = None
        self.username = None
        self.seq_num = 0  
        self.unacked_packets = {} 
        self.unacked_lock = threading.Lock()
        
       
        self.private_target = None  
        self.user_buttons = {}     
        self.ping_window = None    
        self.ping_labels = {}
        self.ping_start_times = {}

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing) 
        self.after(100, self.show_login_dialog) 

    def create_widgets(self):
        """Creates and arranges all the GUI widgets in the main window."""
        
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1); self.grid_rowconfigure(1, weight=0); self.grid_rowconfigure(2, weight=0)

 
        self.left_frame = ctk.CTkFrame(self); self.left_frame.grid(row=0, column=0, rowspan=3, padx=10, pady=10, sticky="nsew"); self.left_frame.grid_rowconfigure(2, weight=1)
        header_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent"); header_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,0), sticky="ew"); header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text="Selected Target:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        self.theme_button = ctk.CTkButton(header_frame, text="☀️", font=("Arial", 18), width=30, command=self.toggle_theme); self.theme_button.grid(row=0, column=1, sticky="e")
        self.target_label = ctk.CTkLabel(self.left_frame, text="Public Chat", font=("Arial", 14, "bold"), text_color=("#00838F", "cyan")); self.target_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")
        self.user_list_frame = ctk.CTkScrollableFrame(self.left_frame, label_text="Online Users"); self.user_list_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.control_frame = ctk.CTkFrame(self.left_frame); self.control_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(10,0), sticky="ew"); self.control_frame.grid_columnconfigure((0, 1), weight=1)
        self.ping_button = ctk.CTkButton(self.control_frame, text="Ping Test", command=self.open_ping_window); self.ping_button.grid(row=0, column=0, padx=(0,5), sticky="ew")
        self.logout_button = ctk.CTkButton(self.control_frame, text="Logout", fg_color="#D32F2F", hover_color="#B71C1C", command=self.logout); self.logout_button.grid(row=0, column=1, padx=(5,0), sticky="ew")

        
        self.chat_area = ctk.CTkScrollableFrame(self, fg_color="transparent"); self.chat_area.grid(row=0, column=1, padx=(0, 10), pady=(10,5), sticky="nsew"); self.chat_area.grid_columnconfigure(0, weight=1)
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent"); self.bottom_frame.grid(row=1, column=1, padx=(0, 10), pady=0, sticky="ew"); self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.message_entry = ctk.CTkEntry(self.bottom_frame, placeholder_text="Type your message here...", font=("Arial", 14)); self.message_entry.grid(row=0, column=0, padx=(0,5), sticky="ew"); self.message_entry.bind("<Return>", lambda event: self.send_message())
        self.send_button = ctk.CTkButton(self.bottom_frame, text="Send", width=120, command=self.send_message); self.send_button.grid(row=0, column=1, padx=5)
        self.log_box = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 11), height=120); self.log_box.grid(row=2, column=1, padx=(0, 10), pady=(5,10), sticky="nsew"); ctk.CTkLabel(self, text="System Logs", font=("Arial", 10, "italic")).grid(row=2, column=1, padx=15, pady=8, sticky="ne")

    def toggle_theme(self):
        """Switches the application's appearance between Light and Dark mode."""
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark": ctk.set_appearance_mode("Light"); self.theme_button.configure(text="🌙")
        else: ctk.set_appearance_mode("Dark"); self.theme_button.configure(text="☀️")
       
        self.update_user_list(list(self.user_buttons.keys() - {"__PUBLIC__"}))
            
    def display_message(self, message, sender):
        """Displays a regular chat message in a styled bubble."""
        is_own_message = sender.startswith("You")
      
        if is_own_message:
            justify = "right"; anchor = "e"; padx = (50, 5)
            bubble_color = ("#3B8ED0", "#1F6AA5"); text_color = "white"
        else:
            justify = "left"; anchor = "w"; padx = (5, 50)
            bubble_color = ("#1565C0", "#1f2b38"); text_color = ("white", "#E0E0E0")
        
      
        bubble_frame = ctk.CTkFrame(self.chat_area, fg_color=bubble_color, corner_radius=10); bubble_frame.grid(row=self.chat_area.grid_size()[1], column=0, padx=padx, pady=4, sticky=anchor)
        
        timestamp = time.strftime("%H:%M"); header_text = f"{sender} - {timestamp}"
        header_label = ctk.CTkLabel(bubble_frame, text=header_text, font=("Arial", 10), text_color=text_color); header_label.pack(anchor=anchor, padx=10, pady=(5,0))
     
        message_label = ctk.CTkLabel(bubble_frame, text=message, font=("Arial", 14), text_color=text_color, wraplength=self.winfo_width() * 0.4, justify=justify); message_label.pack(anchor=anchor, padx=10, pady=(0,5), fill="x")
        
        self.after(10, self.scroll_to_bottom)
        
    def scroll_to_bottom(self): self.chat_area._parent_canvas.yview_moveto(1.0)
    
    def send_message(self):
        """Prepares and sends a message packet to the server via UDP."""
        message = self.message_entry.get().strip()
        if not message or not self.tcp_socket: return
        self.seq_num += 1
        payload = {'text': message}
       
        if self.private_target is not None:
            payload['recipient'] = self.private_target; msg_type = protocol.MSG_TYPE_PRIVATE_TEXT_UDP
            display_sender = f"You -> {self.private_target}"; self.log_system_message(f"Sending PM to '{self.private_target}' via UDP.", "white")
        else:
            msg_type = protocol.MSG_TYPE_TEXT_BROADCAST_UDP; display_sender = "You"
            self.log_system_message(f"Sending public message via UDP.", "white")
        
        packet = protocol.pack_data(msg_type, self.username, self.seq_num, payload)
        try:
            self.udp_socket.sendto(packet, (protocol.SERVER_HOST, protocol.UDP_PORT))
            
            with self.unacked_lock: self.unacked_packets[self.seq_num] = {'packet': packet, 'time': time.time()}
        except Exception as e:
            self.display_message_system(f"Message could not be sent: {e}", "ERROR"); self.log_system_message(f"Failed to send message: {e}", "red"); return
        
        self.display_message(message, display_sender); self.message_entry.delete(0, 'end')

    def display_message_system(self, message, sender):
        """Displays a system or error message in the center of the chat area."""
        bubble_frame = ctk.CTkFrame(self.chat_area, fg_color="transparent"); bubble_frame.grid(row=self.chat_area.grid_size()[1], column=0, pady=5, sticky="ew")
        system_color = ("#00838F", "#00BCD4"); error_color = ("#C62828", "#F44336")
        color = system_color if sender == "SYSTEM" else error_color
        label = ctk.CTkLabel(bubble_frame, text=message, text_color=color, font=("Arial", 12, "italic")); label.pack()
        self.after(10, self.scroll_to_bottom)

    def show_login_dialog(self):
        """Prompts the user for a username before connecting."""
        dialog = ctk.CTkInputDialog(text="Enter your username:", title="Login"); username = dialog.get_input()
        if username and username.strip(): self.username = username.strip(); self.title(f"Network Project Chat - {self.username}"); self.connect_to_server()
        else: self.destroy()

    def log_system_message(self, message, color="white"):
        """Writes a formatted message to the System Logs panel."""
        self.log_box.configure(state="normal"); timestamp = time.strftime("%H:%M:%S")
        mode = ctk.get_appearance_mode();
        dark_colors = {"green": "#4CAF50", "red": "#F44336", "yellow": "#FFEB3B", "cyan": "#00BCD4", "orange": "#FF9800", "white": "#FFFFFF"}
        light_colors = {"green": "#00695C", "red": "#C62828", "yellow": "#B96F00", "cyan": "#00838F", "orange": "#E65100", "white": "#000000"}
        colors = light_colors if mode == "Light" else dark_colors
        for c_name, c_hex in colors.items(): self.log_box.tag_config(f"log_{c_name}", foreground=c_hex)
        self.log_box.insert("end", f"({timestamp}) {message}\n", f"log_{color}"); self.log_box.see("end"); self.log_box.configure(state="disabled")

    def connect_to_server(self):
        """Establishes TCP and UDP sockets and connects to the server."""
        self.log_system_message(f"Connecting to {protocol.SERVER_HOST}:{protocol.TCP_PORT}...", "yellow")
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM); self.tcp_socket.connect((protocol.SERVER_HOST, protocol.TCP_PORT)); self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.udp_socket.bind(('', 0)); self.log_system_message("Connection successful.", "green")
            login_packet = protocol.pack_data(protocol.MSG_TYPE_LOGIN, self.username, 0, {}); self.tcp_socket.sendall(login_packet)
            
            threading.Thread(target=self.listen_tcp, daemon=True).start()
            threading.Thread(target=self.retransmit_checker, daemon=True).start()
            self.display_message_system(f"Welcome to the chat, {self.username}!", "SYSTEM")
        except Exception as e:
            self.log_system_message(f"Connection failed: {e}", "red"); self.display_message_system(f"Could not connect to the server.", "ERROR"); self.after(2000, self.destroy)

    def listen_tcp(self):
        """Continuously listens for incoming data on the TCP socket."""
        while True:
            try:
                header_bytes = self.tcp_socket.recv(protocol.HEADER_SIZE);
                if not header_bytes: break
                msg_type, sender_id, seq_num, payload_len = protocol.unpack_header(header_bytes); payload_bytes = b'';
                if payload_len > 0: read_len = 0;
                while read_len < payload_len: chunk = self.tcp_socket.recv(payload_len-read_len); payload_bytes += chunk; read_len += len(chunk)
                payload = protocol.unpack_payload(payload_bytes)
                
                
                if msg_type == protocol.MSG_TYPE_ACK_TCP:
                    with self.unacked_lock:
                        if seq_num in self.unacked_packets: del self.unacked_packets[seq_num]
                    self.after(0, self.log_system_message, f"ACK received for UDP packet #{seq_num}.", "cyan")
                elif msg_type == protocol.MSG_TYPE_PING_REQUEST_TCP:
                    self.after(0, self.log_system_message, f"Received PING request from '{sender_id}'. Responding...", "cyan")
                    response_payload = {'recipient': sender_id}; response_packet = protocol.pack_data(protocol.MSG_TYPE_PING_RESPONSE_TCP, self.username, 0, response_payload); self.tcp_socket.sendall(response_packet)
                elif msg_type == protocol.MSG_TYPE_PING_RESPONSE_TCP:
                    end_time = time.time()
                    if sender_id in self.ping_start_times: start_time = self.ping_start_times.pop(sender_id); rtt = (end_time - start_time) * 1000; self.after(0, self.log_system_message, f"PING response from '{sender_id}' received. RTT: {rtt:.0f} ms.", "cyan"); self.after(0, self.update_ping_label, sender_id, f"{rtt:.0f} ms")
                elif msg_type == protocol.MSG_TYPE_USER_LIST_TCP:
                    self.after(0, self.update_user_list, payload['users'])
                elif msg_type in [protocol.MSG_TYPE_TEXT_BROADCAST_UDP, protocol.MSG_TYPE_PRIVATE_TEXT_UDP]:
                    is_private_msg = msg_type == protocol.MSG_TYPE_PRIVATE_TEXT_UDP
                    display_sender = f"{sender_id} (Private)" if is_private_msg else sender_id
                    self.after(0, self.display_message, payload['text'], display_sender)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                self.after(0, self.log_system_message, "Connection to server lost.", "red"); self.after(0, self.display_message_system, "You have been disconnected.", "ERROR"); break
            except Exception as e:
                print(f"TCP listen error: {e}"); break
            
    def retransmit_checker(self):
        """Periodically checks for unacknowledged UDP packets and retransmits them."""
        while True:
            time.sleep(1); now = time.time()
            with self.unacked_lock:
                for seq_num, info in list(self.unacked_packets.items()):
                    if now - info['time'] > protocol.RETRANSMIT_TIMEOUT:
                        self.after(0, self.log_system_message, f"Packet #{seq_num} timed out. Retransmitting...", "yellow")
                        self.udp_socket.sendto(info['packet'], (protocol.SERVER_HOST, protocol.UDP_PORT))
                        info['time'] = now
                        
    def update_user_list(self, new_users_list):
        """Redraws the online user list, applying correct theme colors."""
        current_users = set(self.user_buttons.keys() - {"__PUBLIC__"}); new_users_set = set(new_users_list)
        joined = new_users_set - current_users; left = current_users - new_users_set
        for user in joined: self.log_system_message(f"User '{user}' has joined the chat.", "green")
        for user in left: self.log_system_message(f"User '{user}' has left the chat.", "orange")
        for widget in self.user_list_frame.winfo_children(): widget.destroy()
        self.user_buttons.clear()

        mode = ctk.get_appearance_mode()
        public_chat_fg_color = ("#EAECEE", "#343638")
        user_button_fg_color = "#AED6F1" if mode == "Light" else "transparent"
        user_button_text_color = "black" if mode == "Light" else "white"

        public_button = ctk.CTkButton(self.user_list_frame, text="Public Chat", command=lambda: self.select_user(None), fg_color=public_chat_fg_color); public_button.pack(fill="x", padx=5, pady=2); self.user_buttons["__PUBLIC__"] = public_button
        for user in sorted(list(new_users_set)):
            button = ctk.CTkButton(self.user_list_frame, text=user, fg_color=user_button_fg_color, text_color=user_button_text_color, border_width=1 if mode == "Dark" else 0, command=partial(self.select_user, user)); button.pack(fill="x", padx=5, pady=2); self.user_buttons[user] = button
        self.select_user(self.private_target)

    def select_user(self, username):
        """Highlights the selected user in the list and sets them as the private message target."""
        mode = ctk.get_appearance_mode()
        public_chat_fg_color = ("#EAECEE", "#343638")
        user_button_fg_color = "#AED6F1" if mode == "Light" else "transparent"
        selected_color = ("#2980B9", "#1F6AA5")

        if "__PUBLIC__" in self.user_buttons: self.user_buttons["__PUBLIC__"].configure(fg_color=public_chat_fg_color)
        for user, button in self.user_buttons.items():
            if user != "__PUBLIC__": button.configure(fg_color=user_button_fg_color)

        self.private_target = username
        private_color = ("#AF601A", "yellow")
        
        if username:
            self.target_label.configure(text=username, text_color=private_color)
            if username in self.user_buttons: self.user_buttons[username].configure(fg_color=selected_color)
        else:
            self.target_label.configure(text="Public Chat", text_color=("#00838F", "cyan"))
            if "__PUBLIC__" in self.user_buttons: self.user_buttons["__PUBLIC__"].configure(fg_color=selected_color)
            
    def logout(self):
        """Logs out from the server and closes the application."""
        if self.tcp_socket:
            try: self.log_system_message("Logging out...", "orange"); self.tcp_socket.sendall(protocol.pack_data(protocol.MSG_TYPE_LOGOUT_TCP, self.username, 0, {}))
            except Exception as e: print(f"Error during logout: {e}")
            finally: self.on_closing()
            
    def open_ping_window(self):
        """Opens a Toplevel window to ping other users."""
        if self.ping_window is not None and self.ping_window.winfo_exists(): self.ping_window.lift(); return
        self.ping_window = ctk.CTkToplevel(self); self.ping_window.title("Network Topology - Ping Test"); self.ping_window.geometry("350x400"); self.ping_window.transient(self); self.ping_window.resizable(False, True)
        main_frame = ctk.CTkScrollableFrame(self.ping_window, label_text="Ping a User"); main_frame.pack(expand=True, fill="both", padx=10, pady=10); main_frame.grid_columnconfigure(0, weight=1)
        self.ping_labels.clear(); online_users = list(self.user_buttons.keys() - {"__PUBLIC__"})
        if not online_users: ctk.CTkLabel(main_frame, text="No other users in chat.").pack(pady=20); return
        for i, user in enumerate(sorted(online_users)):
            row_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); row_frame.grid(row=i, column=0, pady=5, sticky="ew"); row_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row_frame, text=user).grid(row=0, column=0, padx=5, sticky="w")
            ping_label = ctk.CTkLabel(row_frame, text="- ms", width=70); ping_label.grid(row=0, column=1, padx=5); self.ping_labels[user] = ping_label
            ping_btn = ctk.CTkButton(row_frame, text="Ping", width=60, command=partial(self.send_ping_request, user)); ping_btn.grid(row=0, column=2, padx=5)
            
    def send_ping_request(self, target_user):
        """Sends a PING request to a specific user."""
        try:
            self.log_system_message(f"Sending PING request to '{target_user}'.", "white")
            self.ping_start_times[target_user] = time.time()
            if self.ping_window and self.ping_window.winfo_exists() and target_user in self.ping_labels: self.ping_labels[target_user].configure(text="...")
            self.tcp_socket.sendall(protocol.pack_data(protocol.MSG_TYPE_PING_REQUEST_TCP, self.username, 0, {'recipient': target_user}))
        except Exception as e: print(f"Could not send ping request: {e}"); self.log_system_message(f"Failed to send PING to '{target_user}'.", "red")
        
    def update_ping_label(self, user, text):
        """Updates the RTT label in the ping window."""
        if self.ping_window and self.ping_window.winfo_exists() and user in self.ping_labels:
            self.ping_labels[user].configure(text=text)
            
    def on_closing(self):
        """Handles cleanup when the main window is closed."""
        if self.ping_window is not None: self.ping_window.destroy()
        if self.tcp_socket:
            try: self.tcp_socket.close()
            except: pass
        if self.udp_socket: self.udp_socket.close()
        self.destroy()

if __name__ == "__main__":
    app = ChatClient()
    app.mainloop()