import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
from peer import QuizPeer

class QuizPeerGUI:
    def __init__(self):
        self.peer = None
        self.server_connected = False
        self.active_timer = None
        self.current_buzzer = None
        self.lock = threading.Lock()

        # Crea la finestra principale
        self.root = tk.Tk()
        self.root.title("Quiz Game")
        self.root.geometry("600x400")

        # Tema scuro
        self.root.configure(bg="#2e2e2e")
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background="#2e2e2e")
        self.style.configure('TEntry', fieldbackground="#3c3c3c", foreground="#ffffff", bordercolor="#444444")
        self.style.configure('TButton', background="#444444", foreground="#ffffff", bordercolor="#5a5a5a", focusthickness=3)
        self.style.configure('TLabelframe', background="#2e2e2e", foreground="#ffffff", bordercolor="#5a5a5a")
        self.style.configure('TLabelframe.Label', background="#2e2e2e", foreground="#ffffff")
        self.style.configure('TEntry', fieldbackground="#1e1e1e", foreground="#ffffff", insertcolor="#ffffff", bordercolor="#444444")


        # Frame principale
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Ruolo e stato
        self.role_label = ttk.Label(self.main_frame, text="Ruolo: Non assegnato", font=("Arial", 14))
        self.role_label.pack(pady=5)

        self.status_label = ttk.Label(self.main_frame, text="Stato: In attesa", font=("Arial", 12))
        self.status_label.pack(pady=5)

        self.start_button = ttk.Button(self.main_frame, text="Inizia", command=self.start_peer)
        self.start_button.pack(pady=10)

        # layout per il frame del presentatore
        self.presenter_frame = ttk.Labelframe(self.main_frame, text="Presentatore", padding=10)

        # Label e campo per la domanda
        ttk.Label(self.presenter_frame, text="Domanda:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.question_entry = ttk.Entry(self.presenter_frame, width=60)
        self.question_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Label e campo per la risposta corretta
        ttk.Label(self.presenter_frame, text="Risposta Corretta:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.answer_entry = ttk.Entry(self.presenter_frame, width=40)
        self.answer_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # Pulsanti "Invia Domanda" e "Classifica"
        self.send_question_button = ttk.Button(self.presenter_frame, text="Invia Domanda", command=self.send_question)
        self.send_question_button.grid(row=4, column=0, padx=5, pady=5)

        self.leaderboard_button = ttk.Button(self.presenter_frame, text="Classifica", command=self.show_leaderboard)
        self.leaderboard_button.grid(row=4, column=1, padx=5, pady=5)

        # Configurazione per il ridimensionamento
        self.presenter_frame.grid_columnconfigure(0, weight=1)
        self.presenter_frame.grid_columnconfigure(1, weight=1)


        # layout per il frame del giocatore
        self.player_frame = ttk.Labelframe(self.main_frame, text="Giocatore", padding=10)

        # Punteggio del giocatore
        self.player_score_label = ttk.Label(self.player_frame, text="Punteggio: 0")
        self.player_score_label.pack(pady=5)

        # Domanda ricevuta
        self.question_label = ttk.Label(self.player_frame, text="Domanda:")
        self.question_label.pack(pady=5)

        self.question_text = ttk.Label(self.player_frame, text="Nessuna domanda ricevuta", wraplength=400, justify="center")
        self.question_text.pack(pady=5)

        # Campo per la risposta
        self.player_answer_entry = ttk.Entry(self.player_frame, width=30)
        self.player_answer_entry.pack(pady=5)

        # Pulsanti "Prenotati" e "Invia risposta"
        button_frame = ttk.Frame(self.player_frame)
        button_frame.pack(pady=10)

        self.buzz_button = ttk.Button(button_frame, text="Prenotati", command=self.handle_buzz)
        self.buzz_button.grid(row=0, column=0, padx=5)
        self.buzz_button.config(state=tk.DISABLED)

        self.submit_button = ttk.Button(button_frame, text="Invia risposta", command=self.submit_answer)
        self.submit_button.grid(row=0, column=1, padx=5)
        self.submit_button.config(state=tk.DISABLED)


        
        # Nascondi entrambi i frame all'inizio
        self.presenter_frame.pack_forget()
        self.player_frame.pack_forget()

    def start_peer(self):
        """Avvia il peer e tenta la connessione al server."""
        if not self.peer:
            self.peer = QuizPeer(server_host='localhost', server_port=12345)
            threading.Thread(target=lambda: self.peer.start_peer_server(self.update_question_gui), daemon=True).start()
            threading.Thread(target=self.connect_to_server_with_status, daemon=True).start()
            self.start_button.config(state="disabled")  # Disabilita il bottone per evitare clic multipli

    def connect_to_server_with_status(self):
        """Gestisce la connessione al server e aggiorna lo stato della GUI."""
        try:
            self.peer.connect_to_server()
            self.server_connected = True
            self.update_status("Connesso")
            threading.Thread(target=self.monitor_role, daemon=True).start()
        except Exception as e:
            self.server_connected = False
            self.update_status("Connessione al server fallita")
            messagebox.showerror("Errore di Connessione", f"Impossibile connettersi al server: {e}")
            self.start_button.config(state="normal")  # Riabilita il bottone se la connessione fallisce

    def update_status(self, status):
        """Aggiorna il testo dello stato nella GUI."""
        self.status_label.config(text=f"Stato: {status}")

    def monitor_role(self):
        """Monitora il ruolo del peer e aggiorna la GUI appena viene assegnato."""
        while not self.peer.role:
            time.sleep(0.1)  # Aspetta per evitare un loop continuo
        self.root.after(0, lambda: self.update_role(self.peer.role))  # Aggiorna la GUI dal thread principale

    def update_role(self, role):
        """Aggiorna il ruolo nella GUI."""
        print(f"Ruolo assegnato: {role}")  # Debug: mostra il ruolo assegnato
        self.role_label.config(text=f"Ruolo: {role.capitalize()} {self.peer.peer_port}")
        if role == "PRESENTER":
            self.show_presenter_gui()
        elif role == "PLAYER":
            self.show_player_gui()

    def show_presenter_gui(self):
        self.player_frame.pack_forget()
        self.presenter_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def show_player_gui(self):
        self.presenter_frame.pack_forget()
        self.player_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    def send_question(self):
        """Invia la domanda ai giocatori."""
        self.send_question_button.config(state=tk.DISABLED)
        question = self.question_entry.get()
        correct_answer = self.answer_entry.get()
        if question and correct_answer:
            threading.Thread(target=self.peer.start_presenter, args=(question, correct_answer), daemon=True).start()
            self.question_entry.delete(0, tk.END)
            self.answer_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Errore", "Inserisci sia la domanda che la risposta corretta!")
            self.send_question_button.config(state=tk.NORMAL)

    def show_leaderboard(self):
        if self.peer:
            leaderboard_window = tk.Toplevel(self.root)
            leaderboard_window.title("Classifica")

            ttk.Label(leaderboard_window, text="Classifica Giocatori", font=("Arial", 16)).pack(pady=10)

            presenter = self.peer.presenter
            scores = {player: score for player, score in self.peer.scores.items() if player != presenter}

            for player, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
                ttk.Label(leaderboard_window, text=f"Player {player[1]}: {score} punti").pack(pady=2)

            ttk.Button(leaderboard_window, text="Chiudi", command=leaderboard_window.destroy).pack(pady=10)



    def update_question_gui(self, message, connection):
        """Aggiorna la GUI con la domanda o la notifica ricevuta."""
        print(message)
        if message["type"] == "END":
            self.root.after(0, lambda: messagebox.showinfo("Notifica", message["message"]))
            self.submit_button.config(state=tk.DISABLED)  # Disabilita il pulsante
            self.update_status("Fine")
            self.send_question_button.config(state=tk.DISABLED)  # Disabilita il pulsante
 
        elif message["type"] == "CORRECT_ANSWER":
            # Notifica di un vincitore
            self.root.after(0, lambda: messagebox.showinfo("Notifica", message["message"]))
            self.submit_button.config(state=tk.DISABLED)  # Disabilita il pulsante
            self.buzz_button.config(state=tk.DISABLED)
            self.send_question_button.config(state=tk.NORMAL)  # Riabilita il bottone
            if self.active_timer is not None:
                self.root.after_cancel(self.active_timer)
                self.active_timer=None
            self.current_buzzer=None
        elif message["type"] == "WRONG_ANSWER":
            self.root.after(0, lambda: messagebox.showinfo("Notifica", message["message"]))
            self.current_buzzer=None
            print("risposta sbagliata libero il buzz, current holder",self.current_buzzer)
            mess=message["peer"]["port"]
            if self.peer.peer_port != mess:
                #print("ci entro")
                self.buzz_button.config(state=tk.NORMAL)
                print("il bottone di", self.peer.peer_port)

        elif message["type"] == "BUZZ":
            self.root.after(0, lambda: messagebox.showinfo("Notifica", message["message"]))
            self.current_buzzer=message["peer"]["port"]
            print("entro e aggiorno current holder",self.current_buzzer)
            self.buzz_button.config(state=tk.DISABLED)
            #self.submit_button.config(state=tk.NORMAL)
        else:
            # Mostra la domanda e abilita il pulsante
            self.current_connection = connection
            self.question_text.config(text=message["question"])
            self.buzz_button.config(state=tk.NORMAL)



    

    def end_game(self):
        """Termina il gioco e invia un messaggio ai giocatori."""
        if self.peer:
            threading.Thread(target=self.peer.notify_end_game, daemon=True).start()
            messagebox.showinfo("Gioco Terminato", "Il gioco è stato terminato dal presentatore.")



    def submit_answer(self):
        """Invia la risposta alla domanda corrente."""
        if hasattr(self, 'current_connection') and self.current_connection:
            answer = self.player_answer_entry.get()
            if not answer:
                messagebox.showwarning("Errore", "Inserisci una risposta prima di inviare!")
                return

            threading.Thread(target=self._process_answer, args=(answer,), daemon=True).start()
        else:
            messagebox.showwarning("Errore", "Nessuna domanda ricevuta a cui rispondere!")

    def _process_answer(self, answer):
        """Gestisce l'invio della risposta e il feedback dal server."""
        try:
            self.current_connection.sendall(answer.encode())
            feedback = self.current_connection.recv(1024).decode()
            print("feedback",feedback)
            if feedback:
                if self.active_timer:
                    print(self.active_timer)
                    self.root.after_cancel(self.active_timer)
                    self.active_timer = None
                    print("timer cancellato")
                self.root.after(0, lambda: self._handle_feedback(feedback))
        except Exception as e:
            print(f"Errore nell'invio della risposta: {e}")
            self.root.after(0, lambda: messagebox.showerror("Errore", "Errore di comunicazione con il server."))


    def disable_answer(self,mess):
        with self.lock:
            """Disabilita il campo risposta dopo 10 secondi."""
            buzz_message = json.dumps({
                "type": "WRONG_ANSWER",
                "message": f"Il peer {self.peer.peer_port} ha impiegato troppo tempo a rispondere!",
                "peer": {
                    "port": self.peer.peer_port,  # Usa solo informazioni serializzabili
                    "host": self.peer.server_host  # Se necessario, aggiungi altre proprietà
                }
            })
            self.peer.notify_all_peers(buzz_message)
            messagebox.showinfo(mess)
            self.buzz_button.config(state=tk.DISABLED)
            self.submit_button.config(state=tk.DISABLED)
            self.active_timer=self.root.after(10000, self.handle_timeout)

    def handle_timeout(self):
            print("il atto", self.current_buzzer)
            if self.current_buzzer is None:
                self.buzz_button.config(state=tk.NORMAL)
        
        

    def handle_buzz(self):
        """Gestisce la prenotazione del giocatore."""
        if hasattr(self, 'current_connection') and self.current_connection:
            with self.lock:
                print("verifico il current_buzzer",self.current_buzzer)
                if self.current_buzzer is None:
                    #self.current_buzzer=self.peer.peer_port
            # Notifica il server che il giocatore si è prenotato
                    buzz_message = json.dumps({
                        "type": "BUZZ", 
                        "message": f"Il peer {self.peer.peer_port} si è prenotato!, ha 10 secondi per rispondere",
                        "peer": {
                                "port": self.peer.peer_port,  # Usa solo informazioni serializzabili
                                "host": self.peer.server_host  # Se necessario, aggiungi altre proprietà
                                }
                            })
                    threading.Thread(target=self.peer.notify_all_peers, args=(buzz_message,), daemon=True).start()

            # Abilita il pulsante invia risposta
                    self.submit_button.config(state=tk.NORMAL)
                    self.buzz_button.config(state=tk.DISABLED)
                    self.active_timer = self.root.after(10000, lambda: self.disable_answer("tempo scaduto"))
                else:
                    print("buzzer_holder",self.current_buzzer)
                    messagebox.showwarning("Errore", "Aspetta il tuo turno!")
        else:
            messagebox.showwarning("Errore", "Nessuna domanda ricevuta a cui prenotarsi!")


    def _handle_feedback(self, feedback):
        try:
            feedback_data = json.loads(feedback)
            if feedback_data['type'] == "CORRECT_ANSWER":
                score = feedback_data['score']
                self.player_score_label.config(text=f"Punteggio: {score}")
                self.current_connection.close()
                self.current_connection = None
            elif feedback_data['type'] == "WRONG_ANSWER":
                self.buzz_button.config(state=tk.DISABLED)
                self.submit_button.config(state=tk.DISABLED)
                self.active_timer=self.root.after(10000, self.handle_timeout)
        except json.JSONDecodeError:
            print("Errore nel parsing del feedback:", feedback)





    def run(self):
        """Avvia il ciclo principale della GUI."""
        self.root.mainloop()

if __name__ == "__main__":
    gui = QuizPeerGUI()
    gui.run()