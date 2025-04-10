import socket
import select
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
class SecureServerCommunications:
    def __init__(self, host='172.23.203.6', port=3390):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(6)
        self.server_socket.setblocking(False)
        print("✅ Serveur démarré, en attente de connexions...")

        self.epoll = select.epoll()
        self.epoll.register(self.server_socket.fileno(), select.EPOLLIN)

        self.connections = {}    # fileno -> socket
        self.client_ids = {}     # fileno -> client_id
        self.next_id = 1         # attribution des IDs

    def run(self):
        try:
            while True:

                events = self.epoll.poll(1)
                for fileno, event in events:
                    if fileno == self.server_socket.fileno():
                        client_socket, addr = self.server_socket.accept()
                        print_colored(f"📥 Nouvelle connexion de {addr}","green")
                        client_socket.setblocking(False)
                        self.epoll.register(client_socket.fileno(), select.EPOLLIN)
                        self.connections[client_socket.fileno()] = client_socket

                        if self.next_id <= 6:
                            self.client_ids[client_socket.fileno()] = self.next_id
                            client_id = self.next_id
                            self.next_id += 1
                            welcome_message = f"Bienvenue sur le serveur de chat ! Votre ID est {client_id}\n"
                            
                        else:
                            welcome_message = "Serveur plein. Connexion refusée.\n"
                            client_socket.send(welcome_message.encode())
                            client_socket.close()
                            continue

                        client_socket.send(welcome_message.encode())

                    elif event & select.EPOLLIN:
                        client_socket = self.connections[fileno]
                        try:
                            data = client_socket.recv(1024).decode('utf-8')
                        except:
                            data = None

                        if data:
                            data = data.strip()
                            if data == "/list":
                                ids = ", ".join(str(cid) for cid in self.client_ids.values())
                                msg = f"Clients connectés : {ids}\n"
                                client_socket.send(msg.encode())
                                continue

                            if ':' in data:
                                try:
                                    dest_id_str, encrypted_msg = data.split(':', 1)
                                    dest_id = int(dest_id_str.strip())
                                    encrypted_msg = encrypted_msg.strip()

                                    sender_id = self.client_ids.get(fileno, '?')
                                    target_fileno = None
                                    for f, cid in self.client_ids.items():
                                        if cid == dest_id:
                                            target_fileno = f
                                            break

                                    if target_fileno and target_fileno in self.connections:
                                        msg_to_send = f"Client {sender_id} -> Vous: {encrypted_msg}"
                                        self.connections[target_fileno].send(msg_to_send.encode())
                                        print(f"📨 {sender_id} -> {dest_id} ({encrypted_msg})")
                                    else:
                                        client_socket.send(f"⚠️ Client {dest_id} introuvable.\n".encode())
                                except Exception as e:
                                    client_socket.send(f"⚠️ Erreur dans le message : {e}\n".encode())
                            else:
                                client_socket.send("⚠️ Format de message invalide. Utilisez 'ID: message'\n".encode())
                        else:
                            print(f"❌ Client {self.client_ids.get(fileno, '?')} déconnecté")
                            self.epoll.unregister(fileno)
                            client_socket.close()
                            del self.connections[fileno]
                            if fileno in self.client_ids:
                                del self.client_ids[fileno]
        except KeyboardInterrupt:
            print("\n🛑 Interruption. Fermeture du serveur...")
        finally:
            self.cleanup()

    def cleanup(self):
        self.epoll.unregister(self.server_socket.fileno())
        self.epoll.close()
        self.server_socket.close()
        for conn in self.connections.values():
            conn.close()
        print("🧹 Serveur arrêté.")


if __name__ == "__main__":
    server = SecureServerCommunications()
    server.run()
