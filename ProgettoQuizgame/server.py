import socket
import threading
import json
import random

class QuizServer:
    def __init__(self, host='localhost', port=12345, players=3, winning_score=3):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Riutilizzo della porta
        try:
            self.server.bind((host, port))
        except OSError as e:
            print(f"Errore durante il binding: {e}")
            self.server.close()
            raise
        self.server.listen(5)
        self.peers = []
        self.players = players
        self.winning_score = winning_score
        self.lock = threading.Lock()


    def handle_client(self, conn, addr):
        print(f"Connessione ricevuta da {addr}")  # Indirizzo e porta effimera della connessione iniziale
        try:
            # Controlla se il numero massimo di peer è già stato raggiunto
            with self.lock:
                if len(self.peers) >= self.players:
                    print(f"Numero massimo di giocatori raggiunto. Rifiutata connessione da {addr}.")
                    conn.sendall(b"ERROR: Player limit reached")
                    conn.close()
                    return

            # Riceve il messaggio di registrazione con il numero di porta del peer
            message = conn.recv(1024).decode()
            data = json.loads(message)

            if data["type"] == "REGISTER":
                peer_host = addr[0]  # Usa l'indirizzo IP dal socket
                peer_port = data["port"]  # Ottieni il numero di porta dal peer
                if not peer_port or not isinstance(peer_port, int):
                    print(f"Errore: Porta non valida ricevuta da {addr}")
                    conn.sendall(b"ERROR: Invalid port")
                    return               
                peer_addr = (peer_host, peer_port)  # Usa l'indirizzo effettivo inviato dal peer

                with self.lock:
                    self.peers.append((conn, peer_addr))  # Salva connessione e indirizzo reale
                print(f"Peer registrato: {peer_addr}")  # Stampa l'indirizzo reale registrato

                conn.sendall(b"REGISTERED")

                # Avvia il gioco se ci sono abbastanza peer registrati
                if len(self.peers) >= self.players:
                    self.start_game()
            else:
                print(f"Messaggio sconosciuto da {addr}: {message}")
        except Exception as e:
            print(f"Errore nella gestione del peer {addr}: {e}")




    def start_game(self):
        print("Avvio del gioco!")
        with self.lock:
            # Seleziona un presentatore dalla lista dei peer registrati
            presenter_conn, presenter_addr = random.choice(self.peers)

            # Notifica tutti i peer dell'inizio della partita
            for conn, addr in self.peers:
                try:
                    conn.sendall(json.dumps({
                        "type": "START",
                        "presenter": presenter_addr,  # Fornisce l'indirizzo del presentatore
                        "peers": [peer[1] for peer in self.peers],
                        "winning_score": self.winning_score
                    }).encode())
                except Exception as e:
                    print(f"Errore nell'invio del messaggio a {addr}: {e}")

            print(f"Presentatore scelto: {presenter_addr}")


    def run(self):
        print("Server in esecuzione...")
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    players = int(input("Inserisci il numero di giocatori: "))
    if players<3:
        players=3
    winning_score = int(input("Inserisci il punteggio necessario per vincere: "))
    if winning_score<0:
        winning_score=3
    server = QuizServer(players=players, winning_score=winning_score)
    server.run()
