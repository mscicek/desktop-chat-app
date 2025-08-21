import socket
import threading
import protocol
import logging
import sys

log = logging.getLogger('ChatServer')
log.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler('server.log', mode='a')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
log.addHandler(file_handler)
log.addHandler(stream_handler)


class ChatServer:
    """The main class for the chat server."""
    def __init__(self, host, tcp_port, udp_port):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       
        self.clients = {} 
        self.clients_lock = threading.Lock()

    def start(self):
        """Binds sockets and starts listening for connections."""
        self.tcp_socket.bind((self.host, self.tcp_port)); self.tcp_socket.listen()
        log.info(f"TCP Server listening on {self.host}:{self.tcp_port}")
        self.udp_socket.bind((self.host, self.udp_port))
        log.info(f"UDP Server listening on {self.host}:{self.udp_port}")

        
        threading.Thread(target=self.handle_udp_messages, daemon=True).start()

        try:
            while True:
                
                conn, addr = self.tcp_socket.accept()
                
                threading.Thread(target=self.handle_tcp_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            log.info("Server is shutting down by user command (Ctrl+C).")
        finally:
            self.tcp_socket.close(); self.udp_socket.close()
            log.info("Server has been shut down.")

    def handle_udp_messages(self):
        """Listens for and processes all incoming UDP packets."""
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(protocol.BUFFER_SIZE)
                header_bytes = data[:protocol.HEADER_SIZE]
                payload_bytes = data[protocol.HEADER_SIZE:]
                msg_type, sender_id, seq_num, _ = protocol.unpack_header(header_bytes)
                payload = protocol.unpack_payload(payload_bytes)

         
                with self.clients_lock:
                    if sender_id in self.clients: self.clients[sender_id]['udp_address'] = addr

                if msg_type == protocol.MSG_TYPE_TEXT_BROADCAST_UDP:
                    log.info(f"Received public UDP message (Seq:{seq_num}) from '{sender_id}', forwarding.")
                    self.broadcast_message(data, sender_id)
                    self.send_ack(sender_id, seq_num)
                elif msg_type == protocol.MSG_TYPE_PRIVATE_TEXT_UDP:
                    recipient = payload.get('recipient')
                    if recipient:
                        log.info(f"Received private UDP message (Seq:{seq_num}) from '{sender_id}' to '{recipient}', forwarding.")
                        self.send_private_message(data, recipient)
                        self.send_ack(sender_id, seq_num)
            except Exception as e:
                log.error(f"Error in UDP handler: {e}", exc_info=True)

    def handle_tcp_client(self, conn, addr):
        """Manages a single client's entire lifecycle via their TCP connection."""
        username = None
        log.info(f"New TCP connection from {addr}, waiting for login...")
        try:
            while True:
           
                header_bytes = conn.recv(protocol.HEADER_SIZE)
                if not header_bytes: break
                
                msg_type, sender_id, _, payload_len = protocol.unpack_header(header_bytes)
                payload_bytes = b''
                if payload_len > 0: payload_bytes = conn.recv(payload_len)
                payload = protocol.unpack_payload(payload_bytes)
                full_packet = header_bytes + payload_bytes

                if msg_type == protocol.MSG_TYPE_LOGIN:
                    with self.clients_lock:
                        if sender_id in self.clients: log.warning(f"Login failed for {addr}: Username '{sender_id}' is already taken."); conn.close(); return
                        username = sender_id
                        self.clients[username] = {'tcp_socket': conn, 'tcp_address': addr}
                    log.info(f"User '{username}' logged in successfully from {addr}.")
                    self.broadcast_user_list()
                
                elif msg_type == protocol.MSG_TYPE_LOGOUT_TCP:
                    log.info(f"User '{sender_id}' initiated a clean logout."); break
                
                elif msg_type == protocol.MSG_TYPE_PING_REQUEST_TCP:
                    recipient = payload.get('recipient')
                    if recipient: log.info(f"PING Request: Forwarding from '{sender_id}' to '{recipient}'."); self.send_private_message(full_packet, recipient)

                elif msg_type == protocol.MSG_TYPE_PING_RESPONSE_TCP:
                    recipient = payload.get('recipient')
                    if recipient: log.info(f"PING Response: Forwarding from '{sender_id}' to '{recipient}'."); self.send_private_message(full_packet, recipient)

        except (ConnectionResetError, BrokenPipeError, OSError):
            log.warning(f"Connection with '{username if username else addr}' dropped unexpectedly.")
        except Exception as e:
            log.error(f"An error occurred with client '{username if username else addr}': {e}", exc_info=True)
        finally:
         
            if username:
                with self.clients_lock:
                    if username in self.clients: del self.clients[username]
                self.broadcast_user_list()
                log.info(f"Cleaned up resources for user '{username}'.")
            conn.close()

    def broadcast_message(self, message, sender_id):
        """Forwards a message to all clients except the sender."""
        with self.clients_lock:
            for user, client_info in self.clients.items():
                if user != sender_id: self.send_to_client(message, client_info)

    def send_private_message(self, message, recipient):
        """Forwards a message to a single, specific recipient."""
        with self.clients_lock:
            if recipient in self.clients: self.send_to_client(message, self.clients[recipient])

    def send_to_client(self, message, client_info):
        """Helper function to send a packet to a client's TCP socket."""
        try:
            client_info['tcp_socket'].sendall(message)
        except (BrokenPipeError, ConnectionResetError):
            log.warning(f"Failed to send message to user at {client_info.get('tcp_address')}. Client might be disconnected.")

    def broadcast_user_list(self):
        """Sends the current list of online users to all connected clients."""
        with self.clients_lock:
            user_list = list(self.clients.keys())
            payload = {'users': user_list}
            message = protocol.pack_data(protocol.MSG_TYPE_USER_LIST_TCP, "SERVER", 0, payload)
            log.info(f"Broadcasting updated user list to {len(user_list)} clients: {user_list}")
            for client_info in list(self.clients.values()):
                try: client_info['tcp_socket'].sendall(message)
                except (BrokenPipeError, ConnectionResetError): pass
    
    def send_ack(self, username, seq_num):
        """Sends a UDP acknowledgment packet to a client over TCP."""
        with self.clients_lock:
            if username in self.clients:
                ack_packet = protocol.pack_data(protocol.MSG_TYPE_ACK_TCP, "SERVER", seq_num, {})
                try:
                    self.clients[username]['tcp_socket'].sendall(ack_packet)
                    log.info(f"Sent ACK for message #{seq_num} to '{username}'.")
                except Exception as e:
                    log.error(f"Failed to send ACK to '{username}': {e}")

if __name__ == "__main__":
    server = ChatServer(protocol.SERVER_HOST, protocol.TCP_PORT, protocol.UDP_PORT)
    server.start()