import socket
import threading
from Crypto.Cipher import AES
import base64
import hashlib
from Crypto.Util.Padding import pad, unpad

def print_colored(message, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[38;5;34m",
        "orange": "\033[93m",  
        "reset": "\033[0m"
    }

    color_code = colors.get(color.lower())
    if not color_code:
        print("Couleur non supportée. Utilise 'red', 'green' ou 'orange'.")
        return

    print(f"{color_code}{message}{colors['reset']}")


class SecureChatClient:
    def __init__(self, host='192.168.1.100', port=3390, password='securepassword'):
        self.host = host
        self.port = port
        self.client_socket = None
        self.key = hashlib.sha256(password.encode()).digest()
        self.running = True
        self.connect()

    def encrypt_message(self, message):
        cipher = AES.new(self.key, AES.MODE_CBC)
        ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))
        return base64.b64encode(cipher.iv + ciphertext).decode()

    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Tentative de connexion à {self.host}:{self.port} ...")
            self.client_socket.connect((self.host, self.port))
            print_colored("Connexion réussie au serveur.","green")
            welcome_message = self.client_socket.recv(1024).decode()
            print(f"Serveur : {welcome_message}")
            print(" Tapez 'ID: message' pour envoyer un message ou '/list' pour voir les clients connectés.")
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            print(f" Erreur de connexion : {e}")
            self.client_socket = None

    def receive_messages(self):
        while self.running:
            try:
                response = self.client_socket.recv(1024).decode()
                if response:
                    # Si le message contient "-> Vous: ", on tente de le décrypter
                    if response.startswith("Clients"):
                        print(response)
                    elif "-> Vous: " in response:
                        prefix, encrypted_part = response.split("-> Vous: ", 1)
                        decrypted = self.decrypt_message(encrypted_part.strip())
                        print(f"{prefix}-> Vous: {decrypted}\n", end="", flush=True)
                    elif ": " in response:
                        # Message normal avec ID et contenu chiffré
                        prefix, encrypted_part = response.split(": ", 1)
                        decrypted = self.decrypt_message(encrypted_part.strip())
                        print(f"{prefix}: {decrypted}\n", end="", flush=True)
                    else:
                        # Message brut, non chiffré
                        print(f"{response}\n", end="", flush=True)
            except Exception as e:
                print(f"Erreur de communication : {e}")
                break

    def decrypt_message(self, encrypted_b64):
        try:
            raw = base64.b64decode(encrypted_b64)
            iv = raw[:AES.block_size]
            ciphertext = raw[AES.block_size:]
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            return decrypted.decode()
        except Exception as e:
            return f"[Message illisible] ({str(e)})"
    def chat(self):
        if not self.client_socket:
            print("Connexion non établie.")
            return
        try:
            while True:
                message = input()
                if message.lower() == "exit":
                    print("Déconnexion...")
                    self.running = False
                    break
                if message.startswith("/list"):
                    self.client_socket.send(message.encode())
                    continue
                if ':' not in message:
                    print("Format invalide. Utilisez 'ID: message'")
                    continue

                recipient_id, msg = message.split(':', 1)
                recipient_id = recipient_id.strip()
                msg = msg.strip()

                if not recipient_id.isdigit():
                    print("L’ID du destinataire doit être un nombre.")
                    continue

                encrypted_msg = self.encrypt_message(msg)
                payload = f"{recipient_id}:{encrypted_msg}"
                self.client_socket.send(payload.encode())
        except Exception as e:
            print(f"Erreur : {e}")

    def close(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
            print("Connexion fermée.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    with SecureChatClient() as client:
        client.chat()