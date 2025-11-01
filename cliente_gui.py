import socket
import tkinter as tk
from tkinter import simpledialog, messagebox, Listbox, END

# --- Configuração do Cliente de Rede ---
# (Esta classe NetworkClient não muda em nada, por isso
#  pode ser omitida para brevidade, mas está aqui para o ficheiro completo)
class NetworkClient:
    def __init__(self):
        self.client_socket = None

    def connect(self, host, port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            welcome_msg = self.client_socket.recv(1024).decode()
            return welcome_msg
        except socket.error as e:
            messagebox.showerror("Erro de Rede", f"Não foi possível ligar ao servidor: {e}")
            return None

    def send_command(self, command):
        try:
            self.client_socket.sendall(command.encode())
            
            if command.upper() == "SAIR":
                self.client_socket.close()
                return "Ligação fechada."

            resposta = self.client_socket.recv(4096).decode()
            
            if not resposta:
                messagebox.showerror("Erro de Rede", "O servidor desligou a ligação.")
                return None
            
            return resposta.strip()

        except socket.error as e:
            messagebox.showerror("Erro de Rede", f"Ligação perdida: {e}")
            return None
            
    def close(self):
        if self.client_socket:
            self.send_command("SAIR")


# --- Configuração da Interface Gráfica (GUI) ---
class App:
    def __init__(self, root):
        self.network = NetworkClient()
        self.root = root
        self.root.title("ShareList - Cliente")
        self.root.geometry("500x400")
        
        self.is_running = True # <-- NOVO: Flag para controlar o auto-update

        # Rótulo de status no fundo
        self.status_label = tk.Label(root, text="Por favor, ligue-se ao servidor.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame principal
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Frame da Lista (Esquerda) ---
        list_frame = tk.Frame(main_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="Tarefas:").pack(anchor=tk.W)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.task_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=self.task_listbox.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_listbox.pack(fill=tk.BOTH, expand=True)

        # --- Frame dos Botões (Direita) ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        tk.Button(button_frame, text="Atualizar Lista", command=self.atualizar_lista).pack(fill=tk.X)
        tk.Button(button_frame, text="Concluir Tarefa", command=self.concluir_tarefa).pack(fill=tk.X, pady=5)
        tk.Button(button_frame, text="Remover Tarefa", command=self.remover_tarefa, bg="#FF5733", fg="white").pack(fill=tk.X)

        # --- Frame de Adicionar (Fundo) ---
        add_frame = tk.Frame(root, pady=10)
        add_frame.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(add_frame, text="Nova Tarefa:").pack(side=tk.LEFT, padx=(10, 0))
        self.new_task_entry = tk.Entry(add_frame)
        self.new_task_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # --- (MELHORIA 1: Ligar o "Enter") ---
        self.new_task_entry.bind("<Return>", self.adicionar_tarefa_event) # <-- NOVO
        
        tk.Button(add_frame, text="Adicionar", command=self.adicionar_tarefa).pack(side=tk.RIGHT, padx=(0, 10))

        # Regista o fecho da janela
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        
        # Inicia a ligação
        self.ligar_ao_servidor()

    def ligar_ao_servidor(self):
        host = simpledialog.askstring("Ligar ao Servidor", "Digite o IP do servidor:", initialvalue="127.0.0.1")
        if not host:
            self.root.destroy()
            return

        welcome_msg = self.network.connect(host, 5050)
        
        if welcome_msg:
            self.status_label.config(text="Ligado a " + host)
            # --- (MELHORIA 2: Iniciar o auto-update) ---
            self.auto_atualizar_loop() # <-- NOVO
        else:
            self.root.destroy()

    # --- (MELHORIA 2: Nova função de auto-update) ---
    def auto_atualizar_loop(self):
        """Chama a si própria a cada 3 segundos para atualizar a lista."""
        if not self.is_running:
            return # Para de atualizar se a app for fechada

        self.atualizar_lista()
        
        # Agenda esta função para ser chamada novamente em 3000ms (3 segundos)
        self.root.after(3000, self.auto_atualizar_loop) # <-- NOVO

    # --- Funções de Lógica ---
    def atualizar_lista(self):
        # Apanha o estado focado para o restaurar depois
        tarefa_focada = self.task_listbox.curselection() # <-- NOVO
        
        resposta = self.network.send_command("LIST")
        if resposta is None: return

        self.task_listbox.delete(0, END)

        if resposta != "Nenhuma tarefa.":
            tarefas = resposta.split('\n')
            for t in tarefas:
                self.task_listbox.insert(END, t)
        
        # Restaura a seleção para não ser inconveniente
        if tarefa_focada:
            self.task_listbox.select_set(tarefa_focada) # <-- NOVO

    # --- (MELHORIA 1: Função 'wrapper' para o Enter) ---
    def adicionar_tarefa_event(self, event):
        """Função chamada pelo 'bind' do Enter. O 'event' é ignorado."""
        self.adicionar_tarefa() # <-- NOVO

    def adicionar_tarefa(self):
        # NOTA: No campo "Nova Tarefa", escreva *apenas* a tarefa (ex: "Comprar pão")
        # Não escreva o comando "ADD"
        tarefa = self.new_task_entry.get()
        if not tarefa:
            messagebox.showwarning("Aviso", "A tarefa não pode estar vazia.")
            return
        
        resposta = self.network.send_command(f"ADD {tarefa}")
        self.status_label.config(text=resposta)
        self.new_task_entry.delete(0, END)
        self.atualizar_lista() # Atualiza logo após adicionar

    def _obter_numero_tarefa_selecionada(self):
        try:
            indice_selecionado = self.task_listbox.curselection()[0]
            return indice_selecionado + 1
        except IndexError:
            messagebox.showwarning("Aviso", "Por favor, selecione uma tarefa na lista primeiro.")
            return None

    def concluir_tarefa(self):
        num_tarefa = self._obter_numero_tarefa_selecionada()
        if num_tarefa is None: return

        resposta = self.network.send_command(f"DONE {num_tarefa}")
        self.status_label.config(text=resposta)
        self.atualizar_lista()

    def remover_tarefa(self):
        num_tarefa = self._obter_numero_tarefa_selecionada()
        if num_tarefa is None: return
        
        if not messagebox.askyesno("Confirmar", "Tem a certeza que quer remover esta tarefa?"):
            return

        resposta = self.network.send_command(f"DEL {num_tarefa}")
        self.status_label.config(text=resposta)
        self.atualizar_lista()
    
    def ao_fechar(self):
        """Função chamada quando o 'X' da janela é premido."""
        self.is_running = False # <-- NOVO: Para o loop de auto-update
        print("A fechar a ligação...")
        self.network.close()
        self.root.destroy()

# --- Iniciar a Aplicação ---
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()