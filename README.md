# WireGuard-Based Encrypted Chat Client

## Project Overview

This project is a secure, UDP-based chat client developed in Python. It features a graphical user interface (GUI) built using `customtkinter` and supports encrypted communication using an adapted WireGuard-like protocol. The application follows a modular architecture that separates encryption, networking, and user interface components, ensuring clarity, maintainability, and reusability.

## Architecture Overview

The system is composed of four main modules:

- **Encryption**: Implements core cryptographic operations such as AEAD encryption, MACs, hashing, key exchange (Diffie-Hellman), and WireGuard-style handshake logic.
- **Encryption Manager**: Manages the session lifecycle, including handshakes, transport key derivation, and secure message encryption/decryption.
- **Chat Client**: Handles all UDP networking logic, message construction, request handling, and background listening.
- **GUI**: Built with `customtkinter`, this module presents the user interface and handles all user interactions. It communicates with the client and encryption modules but does not manage networking or security directly.

## Chat Protocol Support

The application implements all core chat commands required by the specification:

- `/CONNECT`, `/DISCONNECT`, `/PING`
- `/SET_USERNAME` to dynamically change usernames
- `/USER_LIST` and `/CHANNEL_LIST` with offset-based pagination
- `/CHANNEL_CREATE`, `/CHANNEL_JOIN`, `/CHANNEL_LEAVE`
- `/CHANNEL_MESSAGE` and `/USER_MESSAGE`
- `/WHOIS` and `/WHOAMI`

Additional features include:

- Offset-based pagination (20 users, 10 channels per page) with "Next" and "Previous" buttons
- Full support for request/response formatting and message parsing
- Context-aware feedback and timestamped chat messages

## Encryption Details

The encryption system adapts the WireGuard protocol for secure messaging:

- Each client and server maintains a pair of static and ephemeral keys.
- Handshake logic involves an initiation and response phase to derive shared session keys.
- Key derivation is performed using a combination of static/ephemeral keys and a KDF.
- Once the handshake is complete, encrypted messages are exchanged over UDP using the derived session keys.

## User Interface & Features

- Clean separation between user list, channel list, and central chat area
- Interactive listboxes for user/channel selection
- Tooltips and well-labeled buttons for ease of use
- **Dark Mode** for user comfort
- **Auto-/HELP** command listing
- **Clear Chat** feature to declutter the interface
- **Command Autocomplete** using `TAB`
- Clickable usernames to prefill direct message inputs
- Distinct error and success notifications

## Code Quality Highlights

- Clear separation of concerns across encryption, networking, and UI
- Modular and testable design
- Robust exception handling in networking threads
- Descriptive function names and meaningful comments

## Contributors

- Julyan van der Westhuizen (VWSJUL003)  
- Keegan O’Brien (OBRKEE001)  
- Angelo Yang (YNGANG003)

## Usage
1. Clone the repository and navigate to the root directory 
2. Run `python chatClientGUI.py` 

> Note: Ensure that your version of python has cutomtkinter installed / install customtkinter 
> Note: At the time of writing, the corresponding chat **server** is up and running - this might not always be the case (so this chat client might end up having nothing to connect to)





