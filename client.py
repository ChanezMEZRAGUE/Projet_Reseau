import socket                    # Pour les connexions réseau
import threading                 # Pour permettre la réception des messages en parallèle
from Crypto.Cipher import AES   # Pour le chiffrement symétrique AES
import base64                   # Pour encoder/décoder les données binaires en texte
import hashlib                  # Pour générer une clé de chiffrement à partir d’un mot de passe
from Crypto.Util.Padding import pad, unpad  # Pour compléter ou retirer le padding des blocs AES

# Fonction utilitaire pour afficher des messages colorés dans le terminal
def print_colored(message, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[38;5;34m",
        "orange": "\033[93m",  
        "reset": "\033[0m"
    }
    color_code = colors.get(color.lower())  # Récupère le code couleur selon le nom
    if not color_code:
        print("Couleur non supportée. Utilise 'red', 'green' ou 'orange'.")
        return
    print(f"{color_code}{message}{colors['reset']}")  # Affiche le message avec la couleur choisie

# Classe principale représentant le client de chat sécurisé
class SecureChatClient:
    def __init__(self, host='192.16', port=3390, password='securepassword'):
        self.host = host  # Adresse IP du serveur
        self.port = port  # Port d'écoute du serveur
        self.client_socket = None  # Socket client
        self.key = hashlib.sha256(password.encode()).digest()  # Génère une clé AES à partir du mot de passe (256 bits)
        self.running = True  # Contrôle l'exécution du thread de réception
        self.connect()  # Tente de se connecter au serveur dès le lancement

    # Méthode pour chiffrer un message texte avec AES CBC
    def encrypt_message(self, message):
        cipher = AES.new(self.key, AES.MODE_CBC)  # Création du chiffreur AES en mode CBC
        ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))  # Ajoute un padding au message puis chiffre
        return base64.b64encode(cipher.iv + ciphertext).decode()  # Ajoute l’IV devant et encode le tout en base64

    # Connexion au serveur et démarrage du thread de réception
    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Création du socket TCP
        try:
            print(f"Tentative de connexion à {self.host}:{self.port} ...")
            self.client_socket.connect((self.host, self.port))  # Connexion au serveur
            print_colored("Connexion réussie au serveur.","green")
            welcome_message = self.client_socket.recv(1024).decode()  # Message d’accueil du serveur
            print(f"Serveur : {welcome_message}")
            print("ℹ️ Tapez 'ID: message' pour envoyer un message ou '/list' pour voir les clients connectés.")
            threading.Thread(target=self.receive_messages, daemon=True).start()  # Lance un thread pour écouter les messages entrants
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            self.client_socket = None

    # Méthode qui tourne en parallèle pour recevoir et afficher les messages entrants
    def receive_messages(self):
        while self.running:
            try:
                response = self.client_socket.recv(1024).decode()  # Attend un message du serveur
                if response:
                    if response.startswith("Clients"):  # Liste des clients
                        print(response)
                    elif "-> Vous: " in response:  # Message chiffré reçu par ce client
                        prefix, encrypted_part = response.split("-> Vous: ", 1)
                        decrypted = self.decrypt_message(encrypted_part.strip())
                        print(f"{prefix}-> Vous: {decrypted}\n", end="", flush=True)
                    elif ": " in response:  # Message chiffré normal
                        prefix, encrypted_part = response.split(": ", 1)
                        decrypted = self.decrypt_message(encrypted_part.strip())
                        print(f"{prefix}: {decrypted}\n", end="", flush=True)
                    else:  # Message brut
                        print(f"{response}\n", end="", flush=True)
            except Exception as e:
                print(f"Erreur de communication : {e}")
                break

    # Déchiffre un message reçu en base64 + AES CBC
    def decrypt_message(self, encrypted_b64):
        try:
            raw = base64.b64decode(encrypted_b64)  # Décodage base64
            iv = raw[:AES.block_size]  # IV est au début
            ciphertext = raw[AES.block_size:]  # Puis le message chiffré
            cipher = AES.new(self.key, AES.MODE_CBC, iv)  # Recrée un chiffreur avec l'IV
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)  # Déchiffre et enlève le padding
            return decrypted.decode()
        except Exception as e:
            return f"[Message illisible] ({str(e)})"

    # Boucle de chat principale pour envoyer les messages
    def chat(self):
        if not self.client_socket:
            print("Connexion non établie.")
            return
        try:
            while True:
                message = input()  # Lecture de la saisie utilisateur
                if message.lower() == "exit":
                    print("Déconnexion...")
                    self.running = False
                    break
                if message.startswith("/list"):  # Commande spéciale pour voir les clients connectés
                    self.client_socket.send(message.encode())
                    continue
                if ':' not in message:  # Vérifie le bon format
                    print("Format invalide. Utilisez 'ID: message'")
                    continue

                recipient_id, msg = message.split(':', 1)
                recipient_id = recipient_id.strip()
                msg = msg.strip()

                if not recipient_id.isdigit():  # Vérifie que l’ID est bien un chiffre
                    print("L’ID du destinataire doit être un nombre.")
                    continue

                encrypted_msg = self.encrypt_message(msg)  # Chiffre le message
                payload = f"{recipient_id}:{encrypted_msg}"  # Construit la chaîne à envoyer
                self.client_socket.send(payload.encode())  # Envoie au serveur
        except Exception as e:
            print(f"Erreur : {e}")

    # Ferme proprement la connexion
    def close(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
            print("Connexion fermée.")

    # Supporte l'utilisation du mot-clé "with"
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

# Point d'entrée du script
if __name__ == "__main__":
    with SecureChatClient() as client:  # Crée un client et le connecte automatiquement
        client.chat()  # Lance la boucle de chat
