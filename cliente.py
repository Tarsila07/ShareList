import socket
import getpass 
#SEM IMPLEMENTAÇÃO GRAFICA (garante pelo menos um codigo funcional)
PORT = 5050
SERVER = input("Digite o IP do servidor: ")

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER, PORT))
    
    
    welcome_msg = client.recv(1024).decode()
    print(welcome_msg, end='') 

except socket.error as e:
    print(f"Erro ao conectar ao servidor {SERVER}:{PORT} - {e}")
    exit()


while True:
    try:
        
        data_do_servidor = client.recv(1024).decode()
        
        if not data_do_servidor:
            print("\nO servidor fechou a ligação.")
            break
            
        
        if (data_do_servidor.endswith(': ') or 
            data_do_servidor.endswith('>> ') or 
            data_do_servidor.endswith('? ')): 
            
            
            
            if data_do_servidor.lower().endswith('senha: '):
                
                msg = input(data_do_servidor) 
            else:
                msg = input(data_do_servidor)
            
            if not msg:
                client.sendall("".encode())
                continue 
            
            client.sendall(msg.encode())
            
            if msg.upper() == "SAIR":
                final_reply = client.recv(1024).decode()
                print(final_reply, end='')
                break 
        
        else:
            
            print(data_do_servidor, end='')

    except (socket.error, ConnectionResetError) as e:
        print(f"\nA ligação ao servidor foi perdida: {e}")
        break

client.close()
print("Ligação fechada.")