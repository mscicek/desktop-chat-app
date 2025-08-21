import struct
import json


SERVER_HOST = '127.0.0.1'  
TCP_PORT = 55555           
UDP_PORT = 55556          
BUFFER_SIZE = 4096         
RETRANSMIT_TIMEOUT = 2.0   

MSG_TYPE_LOGIN = 0x01              
MSG_TYPE_TEXT_BROADCAST_UDP = 0x03  
MSG_TYPE_ACK_TCP = 0x04             
MSG_TYPE_USER_LIST_TCP = 0x05      
MSG_TYPE_PRIVATE_TEXT_UDP = 0x06
MSG_TYPE_LOGOUT_TCP = 0x09
MSG_TYPE_PING_REQUEST_TCP = 0x0A
MSG_TYPE_PING_RESPONSE_TCP = 0x0B

HEADER_FORMAT = '! B 16s I I'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def pack_data(msg_type, sender_id, seq_num, payload_data):
    """
    Packs the given data into a binary packet according to the protocol.
    The payload is converted to a JSON string.
    """

    sender_id_bytes = sender_id.encode('utf-8')
    padded_sender_id = sender_id_bytes.ljust(16, b'\0')

    payload_json = json.dumps(payload_data)
    payload_bytes = payload_json.encode('utf-8')

    header = struct.pack(HEADER_FORMAT, msg_type, padded_sender_id, seq_num, len(payload_bytes))

    return header + payload_bytes

def unpack_header(header_bytes):
    """
    Unpacks the binary header and returns its components as a tuple.
    """
    msg_type, padded_sender_id, seq_num, payload_len = struct.unpack(HEADER_FORMAT, header_bytes)
    
    
    sender_id = padded_sender_id.decode('utf-8').strip('\x00')
    
    return msg_type, sender_id, seq_num, payload_len

def unpack_payload(payload_bytes):
    """
    Unpacks the payload from a JSON byte string into a Python dictionary.
    """
    try:
        return json.loads(payload_bytes.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        
        return None