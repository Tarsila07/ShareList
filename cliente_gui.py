# cliente_gui.py (Versão 6.3 - interface)

import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import socket
import threading
import json
import time

PORT = 5050
BUFFER_SIZE = 2048

class ShareListApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ShareList Client v6.4")
        self.geometry("500x550")
        self.client_socket = None
        self.username = None
        self.current_list = None
        self.stop_updater = False
        self.server_ip = None
        self.task_vars = []
        self.connected = False 
        self.create_ip_screen()

    # Tela inicial: conexão ao servidor
    def create_ip_screen(self):
        self.clear_window()
        tk.Label(self, text="Conectar ao Servidor", font=("Helvetica", 18, "bold")).pack(pady=30)
        tk.Label(self, text="Digite o IP do servidor:").pack(pady=10)

        self.entry_ip = tk.Entry(self, width=30)
        self.entry_ip.pack(pady=5)
        self.entry_ip.bind("<Return>", lambda event: self.connect_to_server())

        tk.Button(self, text="Conectar", bg="#4CAF50", fg="white", width=20,
                  command=self.connect_to_server).pack(pady=15)

    def connect_to_server(self):
        ip = self.entry_ip.get()
        if not ip:
            messagebox.showwarning("Campo vazio", "Digite o IP do servidor.")
            return
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, PORT))
            self.connected = True  # marca como conectado
            self.server_ip = ip
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar: {e}")
            return

        self.create_login_screen()
        threading.Thread(target=self.listen_server, daemon=True).start()

    # ------------------ LOGIN ------------------
    def create_login_screen(self):
        self.clear_window()
        tk.Label(self, text="ShareList - Login", font=("Helvetica", 18, "bold")).pack(pady=20)
        tk.Label(self, text="Usuário:").pack()
        self.entry_user = tk.Entry(self, width=30)
        self.entry_user.pack(pady=5)
        tk.Label(self, text="Senha:").pack()
        self.entry_pass = tk.Entry(self, show="*", width=30)
        self.entry_pass.pack(pady=5)

        tk.Button(self, text="Entrar", bg="#4CAF50", fg="white", width=20,
                  command=self.login_user).pack(pady=10)
        tk.Button(self, text="Registrar", width=20, command=self.register_user).pack(pady=5)
        tk.Button(self, text="< Voltar", width=20, command=self.create_ip_screen).pack(pady=10)

    def login_user(self):
        self.username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not self.username or not password:
            messagebox.showwarning("Campos Vazios", "Preencha usuário e senha.")
            return
        self.send_command(f"LOGIN {self.username} {password}")

    def register_user(self):
        self.username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not self.username or not password:
            messagebox.showwarning("Campos Vazios", "Preencha usuário e senha.")
            return
        self.send_command(f"REGISTER {self.username} {password}")

    # ------------------ LOBBY ------------------
    def show_lobby(self):
        self.clear_window()
        tk.Label(self, text=f"Bem-vindo, {self.username}!", font=("Helvetica", 14)).pack(pady=10)
        tk.Button(self, text="Ver Minhas Listas", width=30,
                  command=lambda: self.send_command("VER")).pack(pady=5)
        tk.Button(self, text="Criar Nova Lista", width=30, command=self.create_list).pack(pady=5)
        tk.Button(self, text="Entrar em Lista (por Código)", width=30, command=self.join_list).pack(pady=5)

        tk.Button(self, text="Sair", width=30, command=self.logout_user).pack(pady=10)

        self.text_box = scrolledtext.ScrolledText(self, height=15, state="disabled")
        self.text_box.pack(fill="both", expand=True, padx=10, pady=10)

    def logout_user(self):
        """Desloga o usuário e volta para a tela de login sem fechar o app"""
        self.stop_updater = True
        try:
            if self.client_socket:
                self.client_socket.sendall("SAIR".encode())
                self.client_socket.close()
        except:
            pass

        # Limpa dados do usuário atual
        self.username = None
        self.current_list = None
        self.client_socket = None
        self.connected = False  # marca como desconectado

        # Retorna para tela de login
        self.after(100, self.create_login_screen)

    def create_list(self):
        titulo = simpledialog.askstring("Nova Lista", "Digite o título da lista:")
        if titulo:
            self.send_command(f"CRIAR {titulo}")

    def join_list(self):
        codigo = simpledialog.askstring("Entrar na Lista", "Digite o código da lista:")
        if codigo:
            self.send_command(f"ENTRAR {codigo.upper()}")

    # ------------------ MODO LISTA ------------------
    def show_list_screen(self, titulo):
        self.clear_window()
        self.current_list = titulo
        tk.Label(self, text=f"📋 {titulo}", font=("Helvetica", 16, "bold")).pack(pady=10)
        add_frame = tk.Frame(self)
        add_frame.pack(fill="x", padx=10, pady=5)
        self.entry_task = tk.Entry(add_frame, width=40)
        self.entry_task.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry_task.bind("<Return>", self.add_task)
        tk.Button(add_frame, text="ADD", bg="#4CAF50", fg="white",
                  command=self.add_task).pack(side="right", padx=5)
        self.list_frame = tk.Frame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        tk.Button(self, text="< Voltar", command=lambda: self.send_command("VOLTAR")).pack(pady=10)
        self.stop_updater = False
        threading.Thread(target=self.auto_update_list, daemon=True).start()

    def add_task(self, event=None):
        desc = self.entry_task.get()
        if desc:
            self.send_command(f"ADD {desc}")
            self.entry_task.delete(0, tk.END)

    def update_list(self, tasks):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.task_vars = []
        for i, t in enumerate(tasks, 1):
            row = tk.Frame(self.list_frame)
            var = tk.BooleanVar(value=t["done"])
            self.task_vars.append(var)
            tk.Checkbutton(row, variable=var,
                           command=lambda idx=i, v=var: self.toggle_task(idx, v)).pack(side="left")
            tk.Label(row, text=t["desc"], anchor="w").pack(side="left", fill="x", expand=True, padx=5)
            tk.Button(row, text="🗑", command=lambda idx=i: self.send_command(f"DEL {idx}"),
                      bg="#f44336", fg="white", width=2).pack(side="right", padx=5)
            row.pack(fill="x", pady=2)

    def toggle_task(self, idx, var):
        cmd = "DONE" if var.get() else "UNDONE"
        self.send_command(f"{cmd} {idx}")

    def auto_update_list(self):
        while not self.stop_updater:
            try:
                self.send_command("LIST")
                time.sleep(2.5)
            except:
                break

    # ------------------ REDE ------------------
    def send_command(self, cmd):
        if not self.connected or not self.client_socket:
            messagebox.showerror("Erro de conexão", "Você foi desconectado do servidor. Reconecte-se.")
            self.create_ip_screen()
            return
        try:
            self.client_socket.sendall(cmd.encode())
        except:
            # se o socket falhar, considera desconectado e volta à tela inicial
            self.connected = False
            messagebox.showerror("Conexão perdida", "O servidor foi desconectado. Reconecte-se.")
            self.create_ip_screen()

    def listen_server(self):
        while True:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    raise ConnectionResetError
                msg = data.decode().strip()
                print("[DEBUG]", msg)
                if msg.startswith("LOGIN_OK"):
                    self.after(0, self.show_lobby)
                elif msg.startswith("LOGIN_NOUSER"):
                    self.after(0, lambda: messagebox.showwarning("Usuário inexistente",
                                                                 "Este usuário não está registrado."))
                elif msg.startswith("LOGIN_WRONGPASS"):
                    self.after(0, lambda: messagebox.showerror("Senha incorreta",
                                                              "Verifique e tente novamente."))
                elif msg.startswith("REGISTER_OK"):
                    self.after(0, lambda: messagebox.showinfo("Sucesso", "Usuário registrado! Faça login."))
                elif msg.startswith("REGISTER_FAIL"):
                    self.after(0, lambda: messagebox.showerror("Erro", "Usuário já existe."))
                elif msg.startswith(("VER_R", "CRIAR_R", "ENTRAR_R")):
                    payload = msg.split(" ", 1)[1] if " " in msg else msg
                    self.after(0, self.show_server_message, payload)
                elif msg.startswith("MODO_LISTA"):
                    titulo = msg.split(" ", 1)[1]
                    self.after(0, self.show_list_screen, titulo)
                elif msg.startswith("LIST_R"):
                    tasks = json.loads(msg.split(" ", 1)[1])
                    self.after(0, self.update_list, tasks)
                elif msg.startswith("MODO_LOBBY"):
                    self.stop_updater = True
                    self.after(0, self.show_lobby)
            except Exception as e:
                print("Erro de conexão:", e)
                self.connected = False
                self.after(0, lambda: messagebox.showerror("Conexão perdida",
                                                         "O servidor foi desconectado. Reconecte-se."))
                self.after(100, self.create_ip_screen)
                break

    # ------------------ INTERFACE ------------------
    def show_server_message(self, msg):
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, msg + "\n")
        self.text_box.config(state="disabled")

    def clear_window(self):
        for w in self.winfo_children():
            w.destroy()

    def on_close(self):
        self.stop_updater = True
        try:
            if self.client_socket:
                self.client_socket.sendall("SAIR".encode())
                self.client_socket.close()
        except:
            pass
        self.destroy()


if __name__ == "__main__":
    app = ShareListApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
