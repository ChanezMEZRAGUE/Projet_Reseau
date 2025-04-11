import socket  # Pour gérer les connexions réseau (sockets)
import select  # Pour la gestion des événements via epoll

class SecureServerCommunications:
    def __init__(self, host='127.0.0.1', port=3390):
        # Crée une socket serveur (IPv4, TCP)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Autorise la réutilisation immédiate de l'adresse après arrêt
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Lie le socket au port spécifié sur l'hôte local
        self.server_socket.bind((host, port))
        
        # Démarre l'écoute sur le socket (maximum 6 connexions en attente)
        self.server_socket.listen(6)
        
        # Met le socket en mode non-bloquant pour éviter les blocages sur accept()
        self.server_socket.setblocking(False)
        print("✅ Serveur démarré, en attente de connexions...")

        # Initialise l’objet epoll pour surveiller les événements sur les sockets
        self.epoll = select.epoll()
        
        # Enregistre le socket serveur dans epoll pour détecter les connexions entrantes
        self.epoll.register(self.server_socket.fileno(), select.EPOLLIN)

        # Dictionnaire pour stocker les connexions client (clé = fileno)
        self.connections = {}

        # Dictionnaire pour stocker les IDs des clients (clé = fileno)
        self.client_ids = {}

        # ID du prochain client à attribuer (max 6 clients)
        self.next_id = 1

    def run(self):
        try:
            while True:
                # Attend des événements sur les sockets surveillés (timeout = 1s)
                events = self.epoll.poll(1)
                
                # Parcours tous les événements détectés
                for fileno, event in events:
                    # Si l'événement vient du socket serveur => nouvelle connexion
                    if fileno == self.server_socket.fileno():
                        client_socket, addr = self.server_socket.accept()  # Accepte la connexion
                        print(f"📥 Nouvelle connexion de {addr}")
                        client_socket.setblocking(False)  # Non-bloquant aussi

                        # Enregistre ce nouveau socket client auprès d’epoll
                        self.epoll.register(client_socket.fileno(), select.EPOLLIN)

                        # Sauvegarde le socket client
                        self.connections[client_socket.fileno()] = client_socket

                        # Si on a encore des IDs à attribuer
                        if self.next_id <= 6:
                            self.client_ids[client_socket.fileno()] = self.next_id
                            client_id = self.next_id
                            self.next_id += 1
                            welcome_message = f"Bienvenue sur le serveur de chat ! Votre ID est {client_id}\n"
                        else:
                            # Si le serveur est plein
                            welcome_message = "Serveur plein. Connexion refusée.\n"
                            client_socket.send(welcome_message.encode())
                            client_socket.close()
                            continue

                        # Envoie le message de bienvenue avec l’ID attribué
                        client_socket.send(welcome_message.encode())

                    # Si l'événement vient d’un client et qu’il a envoyé quelque chose
                    elif event & select.EPOLLIN:
                        client_socket = self.connections[fileno]
                        try:
                            data = client_socket.recv(1024).decode('utf-8')  # Lit le message envoyé
                        except:
                            data = None

                        if data:
                            data = data.strip()
                            
                            # Si le client demande la liste des connexions
                            if data == "/list":
                                ids = ", ".join(str(cid) for cid in self.client_ids.values())
                                msg = f"Clients connectés : {ids}\n"
                                client_socket.send(msg.encode())
                                continue

                            # Si le message est destiné à un autre client : ID: message
                            if ':' in data:
                                try:
                                    dest_id_str, encrypted_msg = data.split(':', 1)
                                    dest_id = int(dest_id_str.strip())  # ID du destinataire
                                    encrypted_msg = encrypted_msg.strip()  # Message

                                    sender_id = self.client_ids.get(fileno, '?')  # ID de l'expéditeur

                                    # Cherche le fileno du client destinataire
                                    target_fileno = None
                                    for f, cid in self.client_ids.items():
                                        if cid == dest_id:
                                            target_fileno = f
                                            break

                                    # Si le destinataire existe, on lui envoie le message
                                    if target_fileno and target_fileno in self.connections:
                                        msg_to_send = f"Client {sender_id} -> Vous: {encrypted_msg}"
                                        self.connections[target_fileno].send(msg_to_send.encode())
                                        print(f"📨 {sender_id} -> {dest_id} ({encrypted_msg})")
                                    else:
                                        # Si le destinataire n'existe pas
                                        client_socket.send(f"⚠️ Client {dest_id} introuvable.\n".encode())
                                except Exception as e:
                                    # Si erreur de parsing du message
                                    client_socket.send(f"⚠️ Erreur dans le message : {e}\n".encode())
                            else:
                                # Message non conforme
                                client_socket.send("⚠️ Format de message invalide. Utilisez 'ID: message'\n".encode())
                        else:
                            # Déconnexion du client
                            print(f"❌ Client {self.client_ids.get(fileno, '?')} déconnecté")
                            self.epoll.unregister(fileno)
                            client_socket.close()
                            del self.connections[fileno]
                            if fileno in self.client_ids:
                                del self.client_ids[fileno]
        except KeyboardInterrupt:
            # Fermeture propre du serveur si interruption clavier (Ctrl+C)
            print("\n🛑 Interruption. Fermeture du serveur...")
        finally:
            # Nettoyage
            self.cleanup()

    def cleanup(self):
        # Désenregistre et ferme tout proprement
        self.epoll.unregister(self.server_socket.fileno())
        self.epoll.close()
        self.server_socket.close()
        for conn in self.connections.values():
            conn.close()
        print("🧹 Serveur arrêté.")

# Si le fichier est exécuté directement
if __name__ == "__main__":
    server = SecureServerCommunications()  # Crée une instance du serveur
    server.run()  # Lance le serveur
