import multiprocessing
import socket
import pickle
import time

class CentralServer(object):

    def __init__(self, client_list=None):
        manager = multiprocessing.Manager()
        if client_list == None:
            self.client_list = manager.list() 
        else:
            self.client_list = manager.list().extend(client_list)
        self.peer_id = multiprocessing.Value('l', 1)
        self.lock = multiprocessing.Lock()

    def client_connect_check(self, index):
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = self.client_list[index][1]
        port = self.client_list[index][2]
        try:
            test_result = test_sock.connect((host, port))
            if test_result == 0:
                print("Client not found")
                del self.client_list[index]
            else:
                index = index + 1
        except socket.error:
            print("Socket connection lost")
            del self.client_list[index]
        test_sock.close()
        return index

    def test_clients_live(self):
        lock = self.lock
        while True:
            time.sleep(5)
            lock.acquire()
            if len(self.client_list) > 0:
                index = 0
                while True:
                    index = self.client_connect_check(index)
                    if index >= len(self.client_list):
                        break
                for i in range(0, len(self.client_list)):
                    print("id before: " + str(self.client_list[i][0]))
                    temp_array = [len(self.client_list[:i]) + 1, self.client_list[i][1],self.client_list[i][2]]
                    self.client_list[i] = temp_array
                    print("id after: " + str(self.client_list[i][0]))
                self.peer_id.value = len(self.client_list) + 1
                print("Clients tested")
            lock.release()

    def peer_list_update(self):
        lock = self.lock
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #host = socket.gethostname()
        host = '127.0.0.1' #used for local test purposes
        port = 20566
        sock.bind((host, port))
        print("Update Listening")
        sock.listen(5)
        while True:
            connection, address = sock.accept()
            lock.acquire()
            connection.send(b'CONNECTED')
            if (connection.recv(4096).decode() == 'Peer List Request'):
                connection.send(str(len(self.client_list)).encode())
            if (connection.recv(4096).decode() == 'OK'):
                for i in range(0, len(self.client_list)):
                    temp = self.client_list[i]
                    if not temp:
                        connection.send(pickle.dumps('EOL'))
                        break
                    pickled_temp = pickle.dumps(temp)
                    connection.send(pickled_temp)
                    if (connection.recv(4096).decode() == 'Element Received'):
                        pass
                if(connection.recv(4096).decode() == 'List Received'):
                    connection.close()
                    lock.release()
            else:
                print("Error incorrect code received")
                connection.close()
                lock.release()

    def listener_socket(self):
        lock = self.lock
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #host = socket.gethostname()
        host = '127.0.0.1' #used for local test purposes
        port = 20560
        sock.bind((host, port))
        print("Listening")
        sock.listen(5)
        while True:
            connection, address = sock.accept()
            lock.acquire()
            print("Socket opened "+str(address))
            connection.send(b'CONNECTED')
            if (connection.recv(4096).decode() == 'THIS PEER'):
                connection.send(b'HOST REQUEST')
            this_peer_host = connection.recv(4096).decode()
            print("Peer host: "+ this_peer_host)
            connection.send(b'PORT REQUEST')
            this_peer_port = int(connection.recv(4096).decode())
            print("Peer port: " + str(this_peer_port))
            peer_details = [self.peer_id.value, this_peer_host, this_peer_port]
            self.peer_id.value = self.peer_id.value + 1
            self.client_list.append(peer_details)
            connection.send(b'PEER RECEIVED')
            if (connection.recv(4096).decode() == 'Peer List Request'):
                connection.send(str(len(self.client_list)).encode())
            if (connection.recv(4096).decode() == 'OK'):
                for i in range(0, len(self.client_list)):
                    temp = self.client_list[i]
                    if not temp:
                        connection.send(pickle.dumps('EOL'))
                        break
                    pickled_temp = pickle.dumps(temp)
                    connection.send(pickled_temp)
                    if (connection.recv(4096).decode() == 'Element Received'):
                        pass
                if(connection.recv(4096).decode() == 'List Received'):
                    connection.close()
                    lock.release()
            else:
                print("Error incorrect code received")
                connection.close()
                lock.release()
        

    def start_server(self):
        server_process = multiprocessing.Process(target=self.listener_socket, args=())
        server_process.daemon = True
        test_clients = multiprocessing.Process(target=self.test_clients_live, args=())
        test_clients.daemon = True
        peer_update = multiprocessing.Process(target=self.peer_list_update, args=())
        peer_update.daemon = True
        server_process.start()
        test_clients.start()
        peer_update.start()
        server_process.join()
        test_clients.join()
        peer_update.join()

        

def main():
    s = CentralServer()
    s.start_server()

if __name__ == "__main__":
    main()
