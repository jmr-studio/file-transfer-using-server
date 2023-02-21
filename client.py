import socket,threading,os,json,time,base64
import tkinter as tk
from tkinter.filedialog import askopenfilename

transfer_list=dict()

def createId():
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
            transfer_list[file_id]['send_size']+=len(data)
            transfer_list[file_id]['progress']=round(transfer_list[file_id]['send_size']/
                                                    transfer_list[file_id]['file_size']*100)
            client.sendall(data)
            send_count+=1

            pbar=chr(9608)*(transfer_list[file_id]['progress']//4)+' '*(25-(transfer_list[file_id]['progress']//4))
            speed=(str(round(transfer_list[file_id]['send_size']/send_count/(1024**2),1))+
                           'MB/s')*(transfer_list[file_id]['progress']<100)
            finish='传输完成！'*(transfer_list[file_id]['progress']>=100)
            print('\r{0}.{1} {2}% |{3}| {4}{5}'.format(transfer_list[file_id]['file_name'],
                                                   transfer_list[file_id]['file_ex'],
                                                  transfer_list[file_id]['progress'],
                                                   pbar,speed,finish),end='',flush=True)
    feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')
    end_time=time.time()
    print("耗时:{0}s".format(round(end_time-st_time,2)))

if __name__ == '__main__':
    ip=input(">>").split(',')
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

        target_ip=input('输入要发送文件的ip\n>>:')
        request={'target_ip':ip}
        message=base64.b64encode(json.dumps(request).encode(encoding='utf-8'))
        client.sendall(request)
        #写到这里


        file_dir=getFileDir()
        file_name,file_ex,file_size=getFileHeader(file_dir)

        id=createId()
        transfer_list[id]={"file_dir":file_dir,'file_name':file_name,'file_ex':file_ex,
                           "file_size":file_size,"send_size":0,"progress":0}

        header={'file_id':id,'file_name':file_name,'file_ex':file_ex,'file_size':file_size}
        client.sendall(base64.b64encode(json.dumps(header).encode(encoding='utf-8')))
        feedback=base64.b64decode(client.recv(1024)).decode(encoding='utf-8')

        sendFile(client,id)
    else:
        if feedback=='Too Many Connections':
            print("连接数量太多，请稍后再试")
        if feedback=='Connection Refused':
            print("对方拒绝了传输")
