import os
import sys
import re
import time
import paramiko
import fabric
import tarfile
from tkinter import *
from tkinter import messagebox
from threading import Thread


# TODO: config
height = 600
width = 700
server_password_default = 'gta'
run_file_endswith = '.sh'
run_cmd = 'bash'
connection_timeout = 10
info_connection_timeout = 2


def get_servers() -> dict:
    servers ={}
    with open('servers.txt', 'r') as f:
        for line in f.readlines():
            line_ = line.split(',')
            line_ = [t.strip() for t in line_]
            name = line_[0]
            url = line_[1]
            url_ = url.split('@')
            user = url_[0]
            ip, port = url_[1].split(':')
            servers[name] = {'user':user, 'ip':ip, 'port':port}
    return servers
servers = get_servers()
# print('servers: ', servers)


def get_envs(env_list_dir='.') -> list:
    envs = []
    for dir in os.listdir(env_list_dir):
        if not os.path.isdir(dir): continue
        if dir.startswith('_'): continue
        envs.append(dir)
    return envs
envs = get_envs()
# print('envs:', envs)


def print_server_info(name):
    server = servers[name]
    return name + ' ' + server['user'] + '@' + server['ip'] + ':' + server['port']


# window
window = Tk()
window.title('autoenv')
screenwidth = window.winfo_screenwidth()
screenheight = window.winfo_screenheight()
alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth-width)/2, (screenheight-height)/2*0.8)
window.geometry(alignstr)


# frame_list
frame_list = Frame()
frame_list.pack(side=TOP, fill=BOTH, expand=True)
list_envs, list_servers = Listbox(frame_list, exportselection=False), Listbox(frame_list, exportselection=False)
scrollnar_envs, scrollnar_servers = Scrollbar(frame_list), Scrollbar(frame_list)
list_envs.config(yscrollcommand=scrollnar_envs.set)
list_servers.config(yscrollcommand=scrollnar_servers.set)
scrollnar_envs.config(command=list_envs.yview)
scrollnar_servers.config(command=list_servers.yview)
list_envs.pack(side=LEFT, fill=BOTH, expand=True)
scrollnar_envs.pack(side=LEFT, fill=Y)
list_servers.pack(side=LEFT, fill=BOTH, expand=True)
scrollnar_servers.pack(side=LEFT, fill=Y)
for name in envs: list_envs.insert('end', name)
for name in servers.keys(): list_servers.insert(END, print_server_info(name))
[list_servers.itemconfig(i, bg='#e0f0ff') for i in range(len(servers.keys())) if i%2]
[list_envs.itemconfig(i, bg='#e0f0ff') for i in range(len(envs)) if i%2]


# frame_console
frame_console = Frame()
frame_console.pack(side=TOP, fill=BOTH, expand=True)
console = Text(frame_console, fg='white', bg='black')
scrollnar_console = Scrollbar(frame_console)
console.config(yscrollcommand=scrollnar_console.set)
scrollnar_console.config(command=console.yview)
console.pack(side=LEFT, fill=BOTH, expand=True)
scrollnar_console.pack(side=LEFT, fill=Y)
class Redirector:
    def __init__(self, text) -> None:
        self.text = text
    def write(self, string):
        def write_():
            self.text.insert('end', string)
            self.text.see('end')
        Thread(target=write_, daemon=True).start()
    def flush(self): pass
sys.stdout = Redirector(console)


# frame_ctl
frame_ctl = Frame(window).pack(side=TOP, fill=X, expand=False)
lb_run = Label(frame_ctl, text='runfile: ').pack(side=LEFT)
runfile_v = StringVar(value='run' + run_file_endswith)
entry_run = Entry(frame_ctl, textvariable=runfile_v, width=12).pack(side=LEFT, fill=X, expand=True)
lb_password = Label(frame_ctl, text='password: ').pack(side=LEFT)
password_v = StringVar(value=server_password_default)
entry_password = Entry(frame_ctl, textvariable=password_v, show='*', width=12).pack(side=LEFT, fill=X, expand=True)


def check():
    try:
        server_name = list_servers.get(list_servers.curselection()).split(' ')[0].strip()
        server = servers[server_name]
    except: return False
    conn = fabric.Connection(server['ip'], user=server['user'], 
        port=int(server['port']), connect_kwargs={"password": password_v.get()}, 
        connect_timeout=info_connection_timeout)
    try: 
        mem = conn.run('free -h | grep Mem', hide='stdout').stdout.strip().split(' ')
        mem = [t for t in mem if len(t)>0]
        disk = conn.run('df ~ -kh | grep G', hide='stdout').stdout.strip().split(' ')
        disk = [t for t in disk if len(t)>0]
    except:
        messagebox.showinfo(title='error', message='connection: ' + server['ip'] + ':' + server['port'])
        conn.close()
        return False
    mem_info = 'mem: ' + mem[2] + '/' + mem[1]
    disk_info = 'disk: ' + disk[2] + '/' + disk[1]
    print('[' + server_name + ']' + '[used/total] ' + mem_info + ', ' + disk_info)
    conn.close()
    return True
btn_info = Button(frame_ctl, text='Info', bg='gray', command=check).pack(side=LEFT, fill=X, expand=True)


def terminal():
    try:
        server_name = list_servers.get(list_servers.curselection()).split(' ')[0].strip()
        server = servers[server_name]
    except: return
    try: env = '~/' + list_envs.get(list_envs.curselection()).strip().replace('-', '/')
    except: env = '~'
    os.system('start cmd /k ssh -t -p ' + server['port'] + ' ' + server['user'] + '@' + server['ip'] + ' \" cd ' + env + '; bash --login\"')
btn_terminal = Button(frame_ctl, text='Terminal', bg='gray', command=terminal).pack(side=LEFT, fill=X, expand=True)


def auth():
    try:
        server_name = list_servers.get(list_servers.curselection()).split(' ')[0].strip()
        server = servers[server_name]
    except: return
    conn = fabric.Connection(server['ip'], user=server['user'], 
        port=server['port'], connect_kwargs={"password": password_v.get()}, 
        connect_timeout=connection_timeout)
    try: 
        pwd = conn.run('cd ~; pwd').stdout.strip()
    except:
        messagebox.showinfo(title='error', message='connection: ' + server['ip'] + ':' + server['port'])
        conn.close()
        return
    join = os.path.join
    pub_key = join(join(os.path.expanduser('~'), '.ssh'), 'id_rsa.pub')
    if not os.path.exists(pub_key): os.system('ssh-keygen -t rsa')
    remote_author_file = pwd + '/.ssh/authorized_keys'
    local_author_file = 'authorized_keys-' + str(round(time.time()*1000))
    try:
        conn.get(remote_author_file, local_author_file)
        with open(local_author_file, 'r') as f: lines = f.readlines()
        lines = [t.strip() for t in lines if len(t)>5]
    except: lines = []
    with open(pub_key, 'r') as f: item = f.readlines()[0].strip()
    if item in lines:
        conn.close()
        os.remove(local_author_file)
        return
    lines.append(item)
    out = '\n'.join(lines)
    with open(local_author_file, 'w') as f: f.write(out)
    try:
        conn.put(local_author_file, remote_author_file)
        conn.run('chmod 600 {}'.format(remote_author_file))
    except Exception as e:
        messagebox.showinfo(title='error', message=str(e))
        conn.close()
        os.remove(local_author_file)
        return
    conn.close()
    os.remove(local_author_file)
    return
btn_auth = Button(frame_ctl, text='Auth', bg='gray', command=auth).pack(side=LEFT, fill=X, expand=True)


btn_dispatch = Button(frame_ctl, text='Dispatch', bg='gray')
def dispatch_():
    try:
        env = list_envs.get(list_envs.curselection()).strip()
        server_name = list_servers.get(list_servers.curselection()).split(' ')[0].strip()
        server = servers[server_name]
    except: return
    notice = messagebox.askokcancel('notice', env + ' -> ' + server_name + '\nrelevant files will be deleted')
    if not notice: return
    print(env, ' -> ', server_name)
    def change_to_lf(endswith):
        for root, _, files in os.walk(env):
            for file in files:
                put_localpath = os.path.realpath(os.path.join(root, file))
                if put_localpath.endswith(endswith):
                    # print('-> lf ' + put_localpath)
                    with open(put_localpath, 'rb') as f: temp = f.read()
                    temp = temp.replace(b'\r\n', b'\n')
                    with open(put_localpath, 'wb') as f: f.write(temp)
    change_to_lf(run_file_endswith)
    # connect
    conn = fabric.Connection(server['ip'], user=server['user'], 
        port=server['port'], connect_kwargs={"password": password_v.get()}, 
        connect_timeout=connection_timeout)
    try: 
        pwd = conn.run('cd ~; pwd').stdout.strip()
    except:
        messagebox.showinfo(title='error', message='connection: ' + server['ip'] + ':' + server['port'])
        conn.close()
        return
    put_remotepath = pwd + '/' + '/'.join(re.split(r'[-]', env))
    try:
        conn.run("mkdir -p {0}; cd {0}".format(put_remotepath))
    except Exception as e:
        messagebox.showinfo(title='error', message=str(e))
        conn.close()
        return
    env_file = env + '-' + str(round(time.time()*1000)) + '.tar.gz'
    try:
        with tarfile.open(env_file, 'w:gz') as tar: tar.add(env, arcname=os.path.basename('.'))
    except Exception as e:
        messagebox.showinfo(title='error', message=str(e))
        conn.close()
        return
    try:
        conn.put(env_file, put_remotepath) # no callback
    except Exception as e:
        messagebox.showinfo(title='error', message=str(e))
        conn.close()
        return
    try:
        conn.run("cd {0}; tar -xzvf {1}; rm -rf {1}".format(put_remotepath, env_file))
    except Exception as e:
        messagebox.showinfo(title='error', message=str(e))
        conn.close()
        os.remove(env_file)
        return
    os.remove(env_file)
    try:
        conn.run("cd {0}; {2} {1}".format(put_remotepath, runfile_v.get(), run_cmd), pty=True, encoding='utf-8')
    except:
        messagebox.showinfo(title='partial success', message=server_name + '\nrunfile failed')
        conn.close()
        return
    messagebox.showinfo(title='success', message=server_name)
    conn.close()
def dispatch():
    def run():
        btn_dispatch.config(state=DISABLED)
        dispatch_()
        btn_dispatch.config(state=NORMAL)
    Thread(target=run, daemon=True).start()
btn_dispatch.config(command=dispatch)
btn_dispatch.pack(side=LEFT, fill=X, expand=True)


window.mainloop()
