# Network Project Chat Application

This project is a multi-user chat application developed for a Computer Networks course. It demonstrates a comprehensive understanding of socket programming, custom protocol design, and network reliability mechanisms over UDP. The application features a modern graphical user interface built with CustomTkinter.

## Features

- **Multi-User Chat:** A central server that manages multiple clients connecting and communicating in real-time.
- **Custom Communication Protocol:** A custom-designed binary protocol with a fixed-size header and a JSON payload for flexible and efficient data transmission.
- **Reliable UDP Messaging:** An implementation of acknowledgments (ACKs) and retransmissions to ensure message delivery over the unreliable UDP protocol.
- **Private & Public Messaging:** Users can send messages to the public chat room or select a specific user from the online list to send a private message.
- **Network Topology Discovery:** The server automatically broadcasts the updated list of online users to all clients whenever a user joins or leaves.
- **Live Ping Test:** A utility window to test the Round-Trip Time (RTT) between the client and other online users, demonstrating real-time network latency measurement.
- **System Event Logging:** A dedicated "System Logs" panel in the client GUI displays important network events like connections, disconnections, ACKs, and retransmissions.
- **Dual-Theme Modern GUI:** A user-friendly interface with switchable dark and light themes for an enhanced user experience.
- **Detailed Server Logging:** The server generates a `server.log` file with detailed, formatted logs of all significant events, including connections, errors, and user activities.

## Project Architecture

The application is built on a **Client-Server architecture**:

- **Server (`server.py`):** A multi-threaded Python application that acts as the central hub. It listens for new client connections, manages user sessions, routes messages (both public and private), and handles the logic for UDP reliability (sending ACKs). It also logs all activities to `server.log`.

- **Client (`client.py`):** A GUI application for the end-user. It handles connecting to the server, sending/receiving messages, displaying online users, and managing user interactions like sending pings and changing themes. It also features a local log panel to show network events to the user.

- **Protocol (`protocol.py`):** A shared module that defines the structure and rules of our custom communication protocol. This ensures that both the client and server can correctly pack and unpack data packets.

### Custom Protocol Design

Our protocol consists of a fixed-size header and a variable-size JSON payload.

**Packet Structure:**

| Field         | Size (Bytes) | Description                                                                                             |
|---------------|--------------|---------------------------------------------------------------------------------------------------------|
| **HEADER**    |              |                                                                                                         |
| `MSG_TYPE`    | 1 Byte       | Specifies the message type (e.g., Login, Logout, Public Message, Ping Request).                         |
| `SENDER_ID`   | 16 Bytes     | The username of the message sender, padded to a fixed length for easy parsing.                          |
| `SEQ_NUM`     | 4 Bytes      | A sequence number, primarily used for tracking UDP packets for the reliability mechanism.                 |
| `PAYLOAD_LEN` | 4 Bytes      | The length of the JSON payload in bytes.                                                                |
| **PAYLOAD**   | Variable     | The actual data of the message, formatted as a JSON string (e.g., `{"text": "Hello"}`). |

## Installation and Usage

### Prerequisites

- Python 3.x
- `customtkinter` library

### Installation

1.  Clone this repository or download the source files.
2.  Install the required Python library:
    ```bash
    pip install customtkinter
    ```

### Usage

1.  **Start the Server:** Open a terminal, navigate to the project directory, and run the server script. The server will start listening for connections.
    ```bash
    python server.py
    ```
    You will see log messages in the terminal, and a `server.log` file will be created.

2.  **Launch Clients:** Open a new terminal for each client you want to run.
    ```bash
    python client.py
    ```
    - A login window will appear. Enter a unique username and click "OK".
    - The main chat window will open. You can now send messages, select users for private messages, test pings, and change the theme.
    - Repeat this step to launch multiple clients and see them interact.

## Performance and Reliability

The project implements a reliability layer over UDP.
- **How it works:** When a client sends a UDP message, it starts a timer. The server, upon receiving the message, sends back an acknowledgment (ACK) packet over the reliable TCP channel.
- **Retransmission:** If the client does not receive an ACK within a set timeout (`2.0` seconds), it assumes the packet was lost and retransmits it. This process is logged in the client's "System Logs" panel as a "timed out" event.
- **Performance:** The "Ping Test" feature can be used to measure the RTT to other clients, providing a practical way to analyze network latency.

---