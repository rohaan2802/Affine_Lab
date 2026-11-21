"""A bounded, loopback-only JSON/TCP implementation of the recorded protocol."""

from contextlib import AbstractContextManager
import json
import socket
import socketserver
import threading
from .crypto import armor, clean_reply, dearmor, decrypt, encrypt, mood_key
from .providers import ProviderError

MAX_MESSAGE = 1024 * 1024


def receive_json(connection: socket.socket) -> dict:
    buffer = bytearray()
    decoder = json.JSONDecoder()
    while len(buffer) <= MAX_MESSAGE:
        part = connection.recv(min(65536, MAX_MESSAGE + 1 - len(buffer)))
        if not part:
            break
        buffer.extend(part)
        if len(buffer) > MAX_MESSAGE:
            raise ValueError("message exceeds 1 MiB")
        try:
            text = buffer.decode("utf-8").lstrip()
            message, end = decoder.raw_decode(text)
        except (UnicodeError, json.JSONDecodeError):
            continue
        if text[end:].strip() or not isinstance(message, dict):
            raise ValueError("expected one JSON object")
        return message
    raise ValueError("connection ended without a complete JSON object")


def encode_request(case: dict) -> dict:
    key = mood_key(case["mood"])
    return {
        "username_enc": encrypt(armor(case["username"]), key),
        "mood": case["mood"],
        "message_enc": encrypt(armor(case["concern"]), key),
        "api_key_enc": "",
    }


def decode_request(request: dict) -> tuple[str, int, str]:
    if set(request) != {"username_enc", "mood", "message_enc", "api_key_enc"}:
        raise ValueError("request must contain the four lab fields")
    if request["api_key_enc"] != "":
        raise ValueError(
            "credentials must stay on the server, not in the local protocol"
        )
    if not all(isinstance(request[k], str) for k in ("username_enc", "message_enc")):
        raise ValueError("encrypted fields must be strings")
    key = mood_key(request["mood"])
    username = dearmor(decrypt(request["username_enc"], key))
    concern = dearmor(decrypt(request["message_enc"], key))
    if not 1 <= len(username) <= 100 or not 1 <= len(concern) <= 2000:
        raise ValueError("input fields exceed the lab's length limits")
    return username, request["mood"], concern


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(300)
        try:
            request = receive_json(self.request)
            username, mood, concern = decode_request(request)
            plain = clean_reply(self.server.provider.generate(username, mood, concern))
            if not plain.strip():
                raise ProviderError("provider returned no alphabetic reply")
            response = {"ciphertext": encrypt(plain, mood_key(mood))}
        except ProviderError as exc:
            response = {"error": str(exc)}
        except (ValueError, OSError):
            response = {
                "error": "Lab request failed; check input/provider configuration privately"
            }
        try:
            self.request.sendall(json.dumps(response).encode())
        except OSError:
            pass


class _TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class LabServer(AbstractContextManager):
    def __init__(self, provider, port: int = 0):
        self.server = _TCPServer(("127.0.0.1", port), _Handler)
        self.server.provider = provider
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def address(self):
        return self.server.server_address

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def exchange(case: dict, address: tuple[str, int]) -> dict:
    if address[0] != "127.0.0.1":
        raise ValueError("this client is restricted to local lab traffic")
    request = encode_request(case)
    with socket.create_connection(address, timeout=300) as connection:
        connection.sendall(json.dumps(request).encode())
        response = receive_json(connection)
    if isinstance(response.get("error"), str):
        raise ProviderError(response["error"])
    if not isinstance(response.get("ciphertext"), str):
        raise ProviderError("server did not return a successful encrypted reply")
    return {
        "request": request,
        "response": response,
        "client_plaintext": decrypt(response["ciphertext"], mood_key(case["mood"])),
    }
