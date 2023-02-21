import socket,threading,os,json,time,base64
import tkinter as tk
from tkinter.filedialog import askopenfilename

mutex=threading.Lock()

def createId():
    t=str(round(time.time()*1000))
    t=t[-16:]
    t=base64.b64encode(t.encode('utf-8')).decode('utf-8')
    return t

class TCPServer():
    def __init__(self,ip_list,port):
        self.ip_list=ip_list
        self.port=port
        self.server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.clients=dict()
        self.transfer_list=dict()
    def recvFile(self,client,file_id):
        st_time=time.time()
        recv_count=0
        with open("./"+self.transfer_list[file_id]["file_name"]+'.'+
            self.transfer_list[file_id]["file_ex"],'wb') as f:
            while self.transfer_list[file_id]['recv_size']<self.transfer_list[file_id]['file_size']:
                data=client.recv(1024*1024*16)
                f.write(data)
                mutex.acquire()
                self.transfer_list[file_id]['recv_size']+=len(data)
                self.transfer_list[file_id]['progress']=round(self.transfer_list[file_id]['recv_size']/
                                                    self.transfer_list[file_id]['file_size']*100)
                mutex.release()
                recv_count+=1

                pbar=chr(9608)*(self.transfer_list[file_id]['progress']//4)+\
                         ' '*(25-(self.transfer_list[file_id]['progress']//4))
                speed=(str(round(self.transfer_list[file_id]['recv_size']/recv_count/(1024**2),1))+
                       'MB/s')*(self.transfer_list[file_id]['progress']<100)
                finish='接收完成！'*(self.transfer_list[file_id]['progress']>=100)
                print('\r{0}.{1} {2}% |{3}| {4}{5}'.format(
                    self.transfer_list[file_id]['file_name'],
                    self.transfer_list[file_id]['file_ex'],
                    self.transfer_list[file_id]['progress'],pbar,speed,finish)
                        ,end='',flush=True)
        message=base64.b64encode("Data Received".encode(encoding='utf-8'))
        client.sendall(message)
        end_time=time.time()
        print("耗时:{0}s".format(round(end_time-st_time,2)))
        self.client_count-=1
        del self.transfer_list[file_id]

    def _start(self):
        client,addr=self.server.accept()
        threading.Thread(target=self._start).start()
        print(addr)
        connection_info=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
        if len(self.clients)>=10:
            message=base64.b64encode('Too Many Connections'.encode(encoding='utf-8'))
            client.sendall(message)
            return
        else:
            message=base64.b64encode('Successfully Connected'.encode(encoding='utf-8'))
            client.sendall(message)

            mutex.acquire()
            id=createId()
            self.clients[id]={'ip':addr[0],'user_name':connection_info['user_name'],'connection':client}
            mutex.release()

            feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
            client.sendall(base64.b64encode(json.dumps({'id':id}).encode(encoding='utf-8')))

            request=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
            #写到这里

            file_id,file_name,file_ex,file_size=json.loads(base64.b64decode(client.recv(1024))
                                                                   .decode(encoding='utf-8')).values()
            # print(file_id,file_name,file_ex,file_size)


            message=base64.b64encode("Data Received".encode(encoding='utf-8'))
            client.sendall(message)

            self.recvFile(client,file_id)
        else:
            message=base64.b64encode('Connection Refused'.encode(encoding='utf-8'))
            client.sendall(message)
            return

    def run(self):
        self.server.bind(('0.0.0.0',self.port))
        self.server.listen()
        print(self.ip_list)
        self._start()

if __name__ == '__main__':
    server=TCPServer(socket.gethostbyname_ex(socket.gethostname()),8001)
    server.run()
