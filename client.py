import socket,threading,os,json,time,base64,easygui
import tkinter as tk
from tkinter.filedialog import askopenfilename

mutex=threading.Lock()
transfer_list=dict()

def createID():
    t=str(round(time.time()*1000))
    t=t[-16:]
    t=base64.b64encode(t.encode('utf-8')).decode('utf-8')
    return t

def getFileDir():
    window=tk.Tk()
    window.geometry("0x0+666666+666666")
    file_dir=askopenfilename()
    window.destroy()
    return file_dir

def getFileHeader(file_dir):
    temp=os.path.basename(file_dir).split(".")
    file_name=''.join(temp[0:-1])
    file_ex=temp[-1]

    file_size=os.path.getsize(file_dir)

    return file_name,file_ex,file_size

def sendFile(client,file_id):
    st_time=time.time()
    send_count=0
    with open(transfer_list[file_id]["file_dir"],'rb') as f:
        while transfer_list[file_id]['send_size']<transfer_list[file_id]['file_size']:
            data=f.read(1024*1024*16)
            mutex.acquire()
            transfer_list[file_id]['send_size']+=len(data)
            transfer_list[file_id]['progress']=round(transfer_list[file_id]['send_size']/
                                                    transfer_list[file_id]['file_size']*100)
            mutex.release()
            client.sendall(data)
            send_count+=1

            #进度条部分，改成gui
            pbar=chr(9608)*(transfer_list[file_id]['progress']//4)+' '*(25-(transfer_list[file_id]['progress']//4))
            speed=(str(round(transfer_list[file_id]['send_size']/send_count/(1024**2),1))+
                           'MB/s')*(transfer_list[file_id]['progress']<100)
            finish='传输完成！'*(transfer_list[file_id]['progress']>=100)
            print('\r{0}.{1} {2}% |{3}| {4}{5}'.format(transfer_list[file_id]['file_name'],
                                                   transfer_list[file_id]['file_ex'],
                                                  transfer_list[file_id]['progress'],
                                                   pbar,speed,finish),end='',flush=True)
    #这里也需要改成gui
    feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
    end_time=time.time()
    print("耗时:{0}s".format(round(end_time-st_time,2)))
    if transfer_list.get(file_id):
        mutex.acquire()
        del transfer_list[file_id]
        mutex.release()

def recvFile(client,file_id):
    st_time=time.time()
    recv_count=0
    with open("./"+transfer_list[file_id]["file_name"]+'.'+
        transfer_list[file_id]["file_ex"],'wb') as f:
        while transfer_list[file_id]['recv_size']<transfer_list[file_id]['file_size']:
            data=client.recv(1024*1024*16)
            f.write(data)
            mutex.acquire()
            transfer_list[file_id]['recv_size']+=len(data)
            transfer_list[file_id]['progress']=round(transfer_list[file_id]['recv_size']/
                                                    transfer_list[file_id]['file_size']*100)
            mutex.release()
            recv_count+=1

            #进度条部分，改成gui
            pbar=chr(9608)*(transfer_list[file_id]['progress']//4)+\
                         ' '*(25-(transfer_list[file_id]['progress']//4))
            speed=(str(round(transfer_list[file_id]['recv_size']/recv_count/(1024**2),1))+
                       'MB/s')*(transfer_list[file_id]['progress']<100)
            finish='接收完成！'*(transfer_list[file_id]['progress']>=100)
            print('\r{0}.{1} {2}% |{3}| {4}{5}'.format(
                    transfer_list[file_id]['file_name'],
                    transfer_list[file_id]['file_ex'],
                    transfer_list[file_id]['progress'],pbar,speed,finish)
                        ,end='',flush=True)
    #这里也需要改成gui
    message=base64.b64encode("Data Received".encode(encoding='utf-8'))
    client.sendall(message)
    end_time=time.time()
    print("耗时:{0}s".format(round(end_time-st_time,2)))
    if transfer_list.get(file_id):
        mutex.acquire()
        del transfer_list[file_id]
        mutex.release()

def handleRequest(ip,id):
    thread_client=socket.socket()
    thread_client.connect((ip,8001))

    connection_info={'connection_type':'THREAD_CLIENT','id':id}
    message=base64.b64encode(json.dumps(connection_info).encode(encoding='utf-8'))
    thread_client.sendall(message)

    feedback=base64.b64decode(thread_client.recv(1024)).decode(encoding='utf-8')
    if feedback=='Successfully Connected':
        request=json.loads(base64.b64decode(thread_client.recv(1024)).decode(encoding='utf-8'))
        threading.Thread(target=handleRequest,args=(ip,id)).start()
        #这里需要gui界面
        op=int(easygui.enterbox('ID为{0}的用户{1}想向您传输文件\n>>:'.format(request['id'],request['user_name'])))
        if op:
            message={'target_id':request['id'],'feedback':'Transfer Agreed'}
            thread_client.sendall(base64.b64encode(json.dumps(message).encode(encoding='utf-8')))

            header=json.loads(base64.b64decode(thread_client.recv(1024)).decode(encoding='utf-8'))
            file_id=createID()
            mutex.acquire()
            transfer_list[file_id]={'file_name':header['file_name'],'file_ex':header['file_ex'],
                                "file_size":header['file_size'],"recv_size":0,"progress":0}
            mutex.release()

            recvFile(thread_client,file_id)
        else:
            message={'target_id':request['id'],'feedback':'Transfer Refused'}
            thread_client.sendall(base64.b64encode(json.dumps(message).encode(encoding='utf-8')))
            thread_client.close()
            return
    
if __name__ == '__main__':
    ip=input(">>")
    client=socket.socket()
    client.connect((ip,8001))

    connection_info={'connection_type':'MAIN_CLIENT','user_name':'TEST'}
    message=base64.b64encode(json.dumps(connection_info).encode(encoding='utf-8'))
    client.sendall(message)

    feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
    if feedback=='Successfully Connected':
        print('连接成功！')
        message=base64.b64encode('Data Received'.encode(encoding='utf-8'))
        client.sendall(message)

        feedback=json.loads(base64.b64decode(client.recv(1024)).decode(encoding='utf-8'))
        threading.Thread(target=handleRequest,args=(ip,feedback['id'])).start()
        print("你的独有ID:",feedback['id'])
        for c in feedback['connection_list']:
            print(c)

        while True:
            target_id=input('>>:')
            request={'target_id':target_id}
            message=base64.b64encode(json.dumps(request).encode(encoding='utf-8'))
            client.sendall(message)
            print('等待对方响应...')

            feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
            if feedback=='Transfer Agreed':
                print("对方同意了文件传输！")
                file_dir=getFileDir()
                file_name,file_ex,file_size=getFileHeader(file_dir)

                id=createID()
                mutex.acquire()
                transfer_list[id]={"file_dir":file_dir,'file_name':file_name,'file_ex':file_ex,
                                   "file_size":file_size,"send_size":0,"progress":0}
                mutex.release()

                client.sendall(base64.b64encode('Transfer Agreed'.encode(encoding='utf-8')))
                feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')

                header={'file_id':id,'file_name':file_name,'file_ex':file_ex,'file_size':file_size}
                client.sendall(base64.b64encode(json.dumps(header).encode(encoding='utf-8')))
                feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')

                sendFile(client,id)
            else:
                if feedback=='Transfer Refused':
                    print("对方拒绝了文件传输！")
    else:
        if feedback=='Too Many Connections':
            print("连接数量太多，请稍后再试")
