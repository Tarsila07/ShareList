# cliente_gui.py (Versão 6.2 - Interface Gráfica Tkinter)

import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import socket
import threading
import json
import time

# Configurações de rede
PORT = 5050
BUFFER_SIZE = 2048

# Classe principal da aplicação cliente
class ShareListApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Configuração inicial da janela
        self.title("ShareList Client v6.2")
        self.geometry("500x550")
        self.client_socket = None
        self.username = None
        self.current_list = None
        self.stop_updater = False
        self.server_ip = None
        self.task_vars = []
        # Tela inicial para conexão ao servidor
        self.create_ip_screen()

    # Tela inicial: conexão ao servidor
    def create_ip_screen(self):
        self.clear_window()
        tk.Label(self, text="Conectar ao Servidor", font=("Helvetica", 18, "bold")).pack(pady=30)
        tk.Label(self, text="Digite o IP do servidor:").pack(pady=10)
        self.entry_ip = tk.Entry(self, width=30)
        self.entry_ip.pack(pady=5)
        tk.Button(self, text="Conectar", bg="#4CAF50", fg="white", width=20,
                  command=self.connect_to_server).pack(pady=15)

    # Estabelece conexão com o servidor via socket
    def connect_to_server(self):
        ip = self.entry_ip.get()
        if not ip:
            messagebox.showwarning("Campo vazio", "Digite o IP do servidor.")
            return
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, PORT))
            self.server_ip = ip
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar: {e}")
            return
        # Após conectar, exibe tela de login
        self.create_login_screen()
        threading.Thread(target=self.listen_server, daemon=True).start()

    # Tela de login e registro de usuário
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

    # Envia comando de login ao servidor
    def login_user(self):
        self.username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not self.username or not password:
            messagebox.showwarning("Campos Vazios", "Preencha usuário e senha.")
            return
        self.send_command(f"LOGIN {self.username} {password}")

    # Envia comando de registro ao servidor
    def register_user(self):
        self.username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not self.username or not password:
            messagebox.showwarning("Campos Vazios", "Preencha usuário e senha.")
            return
        self.send_command(f"REGISTER {self.username} {password}")

    # Tela principal após login (lobby)
    def show_lobby(self):
        self.clear_window()
        tk.Label(self, text=f"Bem-vindo, {self.username}!", font=("Helvetica", 14)).pack(pady=10)
        tk.Button(self, text="Ver Minhas Listas", width=30,
                  command=lambda: self.send_command("VER")).pack(pady=5)
        tk.Button(self, text="Criar Nova Lista", width=30, command=self.create_list).pack(pady=5)
        tk.Button(self, text="Entrar em Lista (por Código)", width=30, command=self.join_list).pack(pady=5)
        tk.Button(self, text="Sair", width=30, command=self.on_close).pack(pady=10)
        # Área de texto para mensagens e retorno do servidor
        self.text_box = scrolledtext.ScrolledText(self, height=15, state="disabled")
        self.text_box.pack(fill="both", expand=True, padx=10, pady=10)

    # Criação de uma nova lista
    def create_list(self):
        titulo = simpledialog.askstring("Nova Lista", "Digite o título da lista:")
        if titulo:
            self.send_command(f"CRIAR {titulo}")

    # Entrar em uma lista existente através do código
    def join_list(self):
        codigo = simpledialog.askstring("Entrar na Lista", "Digite o código da lista:")
        if codigo:
            self.send_command(f"ENTRAR {codigo.upper()}")

    # Exibe a tela de uma lista com tarefas
    def show_list_screen(self, titulo):
        self.clear_window()
        self.current_list = titulo
        tk.Label(self, text=f"📋 {titulo}", font=("Helvetica", 16, "bold")).pack(pady=10)
        # Campo para adicionar novas tarefas
        add_frame = tk.Frame(self)
        add_frame.pack(fill="x", padx=10, pady=5)
        self.entry_task = tk.Entry(add_frame, width=40)
        self.entry_task.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry_task.bind("<Return>", self.add_task)
        tk.Button(add_frame, text="ADD", bg="#4CAF50", fg="white",
                  command=self.add_task).pack(side="right", padx=5)
        # Área onde as tarefas serão exibidas
        self.list_frame = tk.Frame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        tk.Button(self, text="< Voltar", command=lambda: self.send_command("VOLTAR")).pack(pady=10)
        # Thread que atualiza a lista periodicamente
        self.stop_updater = False
        threading.Thread(target=self.auto_update_list, daemon=True).start()

    # Adiciona uma nova tarefa
    def add_task(self, event=None):
        desc = self.entry_task.get()
        if desc:
            self.send_command(f"ADD {desc}")
            self.entry_task.delete(0, tk.END)

    # Atualiza visualmente as tarefas na tela
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

    # Marca ou desmarca uma tarefa como concluída
    def toggle_task(self, idx, var):
        cmd = "DONE" if var.get() else "UNDONE"
        self.send_command(f"{cmd} {idx}")

    # Atualiza automaticamente a lista a cada 2.5 segundos
    def auto_update_list(self):
        while not self.stop_updater:
            try:
                self.send_command("LIST")
                time.sleep(2.5)
            except:
                break

    # Envia um comando genérico ao servidor
    def send_command(self, cmd):
        try:
            self.client_socket.sendall(cmd.encode())
        except:
            pass

    # Thread responsável por receber mensagens do servidor
    def listen_server(self):
        while True:
            try:
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                msg = data.decode().strip()
                print("[DEBUG]", msg)
                # Interpreta mensagens do servidor e atualiza interface
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
                elif msg.startswith("VER_R") or msg.startswith("CRIAR_R") or msg.startswith("ENTRAR_R"):
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
                break

    # Exibe mensagens retornadas pelo servidor
    def show_server_message(self, msg):
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, msg + "\n")
        self.text_box.config(state="disabled")

    # Limpa todos os widgets da janela atual
    def clear_window(self):
        for w in self.winfo_children():
            w.destroy()

    # Finaliza conexão e fecha o aplicativo
    def on_close(self):
        self.stop_updater = True
        try:
            if self.client_socket:
                self.client_socket.sendall("SAIR".encode())
                self.client_socket.close()
        except:
            pass
        self.destroy()

# Execução principal do aplicativo
if __name__ == "__main__":
    app = ShareListApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
