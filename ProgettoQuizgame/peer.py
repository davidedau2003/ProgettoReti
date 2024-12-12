import socket
import threading
import json
import sys

class QuizPeer:
    def __init__(self, server_host='localhost', server_port=12345, winning_score=3):
        self.server_host = server_host
        self.server_port = server_port
        self.peer_host = 'localhost'
        self.peer_port = None  # Sarà impostata dinamicamente
        self.presenter = None
        self.peers = []
        self.role = None
        self.listener_thread = None
        self.scores = {}  # Dizionario {peer: punteggio}
        self.winning_score = winning_score  # Punteggio necessario per vincere
        

    def start_peer_server(self, callback):
        """Avvia un socket server per ricevere domande."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.peer_host, 0))  # Usa una porta disponibile
        self.peer_port = self.server_socket.getsockname()[1]
        print(f"Peer in ascolto su {self.peer_host}:{self.peer_port}")
        self.server_socket.listen(5)

        # Thread per accettare connessioni in ingresso
        self.listener_thread = threading.Thread(target=self.listen_for_questions, args=(callback,), daemon=True)
        self.listener_thread.start()

    def listen_for_questions(self, on_question_received):
        """Ascolta le domande inviate dal presentatore e notifica la GUI."""
        while True:
            try:
                conn, addr = self.server_socket.accept()
                message = conn.recv(1024).decode().strip()  # Decodifica il messaggio e rimuove spazi bianchi
                if not message:
                    print(f"Messaggio vuoto ricevuto da {addr}.")
                    conn.close()
                    continue
                
                try:
                    data = json.loads(message)  # Prova a caricare il JSON
                except json.JSONDecodeError as e:
                    print(f"Errore nel parsing del JSON: {e}. Messaggio ricevuto: {message}")
                    conn.close()
                    continue

                if data["type"] == "QUESTION":
                    question = data["question"]
                    print(f"Domanda ricevuta: {question}")
                    on_question_received(data, conn)
                elif data["type"] == "CORRECT_ANSWER":
                    notification = data["message"]
                    print(f"Notifica ricevuta: {notification}")
                    on_question_received(data, None)  # Passa il messaggio alla GUI
                elif data["type"] == "END":
                    on_question_received(data, None)
                    conn.close()
                    break
                elif data["type"] == "BUZZ":
                    on_question_received(data, None)
                    # Puoi notificare tutti gli altri peer che un giocatore si è prenotato
                    #self.notify_all_peers(notification)
                elif data["type"] == "WRONG_ANSWER":
                    on_question_received(data,None)
            except Exception as e:
                print(f"Errore nella ricezione del messaggio: {e}")






    def connect_to_server(self):
        """Connetti al server centrale e registrati."""
        print("Connettendo al server centrale...")
        try:
            self.server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_conn.connect((self.server_host, self.server_port))
            registration_message = {
                "type": "REGISTER",
                "port": self.peer_port  # Invia il numero di porta su cui il peer è in ascolto
            }
            self.server_conn.sendall(json.dumps(registration_message).encode())
            response = self.server_conn.recv(1024).decode()
            if response == "REGISTERED":
                print("Registrato al server centrale. In attesa della partita...")
                self.listen_for_game()
            else:
                print(f"Registrazione fallita: {response}")
                raise Exception("Risposta di registrazione non valida: " + response)  # Se la risposta non è "REGISTERED", solleva un'eccezione
        except socket.error as e:
            # Gestisce gli errori di connessione (ad esempio, server non raggiungibile)
            raise Exception(f"Errore di connessione al server: {e}")
        except Exception as e:
            # Gestisce altri errori generici, come una risposta errata dal server
            raise Exception(f"Errore durante la registrazione al server: {e}")

    def listen_for_game(self):
        """Attende il messaggio di inizio partita dal server."""
        while True:
            try:
                message = self.server_conn.recv(1024).decode()
                if not message:
                    print("Connessione al server persa.")
                    break
                data = json.loads(message)
                if data["type"] == "START":
                    self.presenter = tuple(data["presenter"])
                    self.peers = [tuple(peer) for peer in data["peers"]]
                    self.scores = {peer: 0 for peer in self.peers}
                    self.winning_score = data.get("winning_score")  # Imposta il punteggio di vittoria
                    if self.presenter == ("127.0.0.1", self.peer_port):
                        self.role = "PRESENTER"
                    else:
                        self.role = "PLAYER"
                    print(f"Ruolo assegnato: {self.role}")  # Log per debug
                    break
            except Exception as e:
                print(f"Errore nel ricevere il messaggio di avvio: {e}")


    def send_question_to_peer(self, peer, question, correct_answer):
        """Invia la domanda a un singolo peer e verifica le risposte."""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(peer)  # Connessione al peer
            print(f"Connessione al peer {peer} per inviare la domanda...")
            
            # Invia la domanda iniziale
            question_message = json.dumps({"type": "QUESTION", "question": question})
            conn.sendall(question_message.encode())

            # Ciclo per ricevere le risposte finché non è corretta
            while True:
                try:
                    response = conn.recv(1024).decode().strip()
                    if not response:  # Peer ha chiuso la connessione
                        continue
                    
                    print(f"Risposta ricevuta da {peer}: {response}")
                    
                    if response.strip().lower() == correct_answer.strip().lower():
                        self.scores[peer] += 1
                        feedback_message = json.dumps({"type": "CORRECT_ANSWER", "score": self.scores[peer]})
                        conn.sendall(feedback_message.encode())

                        # Notifica tutti gli altri peer
                        notification = {
                            "type": "CORRECT_ANSWER",
                            "message": f"Il player {peer[1]} ha risposto correttamente!"
                        }
                        self.notify_all_peers(json.dumps(notification))

                        # Controlla la vittoria
                        if self.scores[peer] >= self.winning_score:
                            print(f"Player {peer[1]} ha vinto la partita con {self.scores[peer]} punti!")
                            self.notify_end_game(peer)
                        break  # Termina il ciclo per questo peer
                    else:

                        # Notifica tutti gli altri peer
                        notification = {
                            "type": "WRONG_ANSWER",
                            "message": f"Il player {peer[1]} ha risposto in maniera errata!",
                            "peer": {
                                "port": peer[1],  # Usa solo informazioni serializzabili
                                "host": peer[0]  # Se necessario, aggiungi altre proprietà
                            }
                        }
                        self.notify_all_peers(json.dumps(notification))
                        feedback_message = json.dumps({"type": "WRONG_ANSWER"})
                        conn.sendall(feedback_message.encode())

                except socket.error as e:
                    print(f"Errore nella comunicazione con il peer {peer}: {e}")
                    break
        finally:
            conn.close()







    def notify_all_peers(self, message):
        """Invia un messaggio a tutti i peer."""
        for peer in self.peers :
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                    conn.connect(peer)
                    conn.sendall(message.encode())
            except Exception as e:
                print(f"Errore nel notificare il peer {peer}: {e}")


    def notify_end_game(self, winner):
        """Notifica a tutti i peer che il gioco è terminato."""
        message = json.dumps({
            "type": "END",
            "message": f"FINE GIOCO: Il player {winner[1]} ha vinto!"
        })
        for peer in self.peers:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                    conn.connect(peer)
                    conn.sendall(message.encode())
            except Exception as e:
                print(f"Errore nel notificare il peer {peer} della fine del gioco: {e}")
        print("Il gioco è terminato.")




    def start_presenter(self, question, correct_answer):
        """Gestisce il ruolo del presentatore."""
        threads = []
        for peer in [p for p in self.peers if p != self.presenter]:
            thread = threading.Thread(target=self.send_question_to_peer, args=(peer, question, correct_answer))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()




    def start_player(self):
        """Gestisce il ruolo del partecipante."""
        print("Sei un partecipante. Attendi una domanda dal presentatore...")
        # Mantieni il peer in ascolto
        while True:
            pass  # Ascolto infinito fino a quando non arriva una domanda

if __name__ == "__main__":
    peer = QuizPeer()
    peer.start_peer_server()
    peer.connect_to_server() 