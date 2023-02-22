import socket,threading,os,json,time,base64,queue
import tkinter as tk
from tkinter.filedialog import askopenfilename

mutex=threading.Lock()

def createID():
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
    def _start(self):
        client,addr=self.server.accept()
        threading.Thread(target=self._start).start()
        print(addr)
        connection_info=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
        if connection_info['connection_type']=='MAIN_CLIENT':
            if len(self.clients)>=10:
                message=base64.b64encode('Too Many Connections'.encode(encoding='utf-8'))
                client.sendall(message)
                return
            else:
                message=base64.b64encode('Successfully Connected'.encode(encoding='utf-8'))
                client.sendall(message)

                mutex.acquire()
                id=createID()
                self.clients[id]={'ip':addr[0],'user_name':connection_info['user_name'],
                                  'connection':client,'thread_clients':queue.Queue()}
                mutex.release()

                feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
                l=[]
                for key,value in self.clients.items():
                    if key==id:
                        continue
                    l.append('{0} {1} {2}'.format(key,value['ip'],value['user_name']))
                message={'id':id,'connection_list':l}
                client.sendall(base64.b64encode(json.dumps(message).encode(encoding='utf-8')))

                while True:
                    request=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
                    target_client=self.clients[request['target_id']]['thread_clients'].get()
                    message={'id':id,'user_name':connection_info['user_name']}
                    target_client.sendall(base64.b64encode(json.dumps(message).encode(encoding='utf-8')))

                    feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
                    client.sendall(base64.b64encode('Data Received'.encode(encoding='utf-8')))
                    if feedback=='Transfer Agreed':
                        t=client.recv(1024)
                        target_client.sendall(t)
                        header=json.loads(base64.b64decode(t).decode(encoding='utf-8'))
                        mutex.acquire()
                        self.transfer_list[header['file_id']]={'file_name':header['file_name'],
                                                               'file_ex':header['file_ex'],
                                                               'file_size':header['file_size'],
                                                               'curr_size':0}
                        mutex.release()

                        print('{0}.{1} 传输中'.format(header['file_name'],header['file_ex']))
                        message=base64.b64encode('Data Received'.encode(encoding='utf-8'))
                        client.sendall(message)

                        while self.transfer_list[header['file_id']]['curr_size']<\
                                self.transfer_list[header['file_id']]['file_size']:
                            data=client.recv(1024*1024*16)
                            mutex.acquire()
                            self.transfer_list[header['file_id']]['curr_size']+=len(data)
                            mutex.release()
                            target_client.sendall(data)

                        feedback=base64.b64decode(target_client.recv(1024)).decode(encoding='utf-8')
                        client.sendall(base64.b64encode('File Received'.encode(encoding='utf-8')))
                        print('{0}.{1} 传输完成！'.format(header['file_name'],header['file_ex']))
                        if self.transfer_list.get(header['file_id']):
                            mutex.acquire()
                            del self.transfer_list[header['file_id']]
                            mutex.release()

                    target_client.close()
                del self.clients[id]
        elif connection_info['connection_type']=='THREAD_CLIENT':
            message=base64.b64encode('Successfully Connected'.encode(encoding='utf-8'))
            client.sendall(message)
            mutex.acquire()
            self.clients[connection_info['id']]['thread_clients'].put(client)
            mutex.release()

            message=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
            self.clients[message['target_id']]['connection']\
                .sendall(base64.b64encode(message['feedback'].encode(encoding='utf-8')))
    def run(self):
        self.server.bind(('0.0.0.0',self.port))
        self.server.listen()
        print(self.ip_list)
        self._start()

if __name__ == '__main__':
    server=TCPServer(socket.gethostbyname_ex(socket.gethostname()),8001)
    server.run()
