import socket

SERVER = input("Digite o IP do servidor: ")
PORT = 5050

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER, PORT))
except socket.error as e:
    print(f"Erro ao conectar ao servidor {SERVER}:{PORT} - {e}")
    exit()


try:
    print(client.recv(1024).decode())
except socket.error as e:
    print(f"Erro ao receber boas-vindas: {e}")
    client.close()
    exit()


while True:
    msg = input(">> ")
    
    
    if not msg:
        continue

    try:
       
        client.sendall(msg.encode())

        
        resposta = client.recv(1024).decode()

        if not resposta:
            print("O servidor desligou a ligação.")
            break
            
        print(resposta, end='')  
                               

        
        if msg.upper() == "SAIR":
            break 

    except socket.error as e:
        print(f"A ligação ao servidor foi perdida: {e}")
        break

client.close()
print("Ligação fechada.")