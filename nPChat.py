#!/usr/bin/python3
# nPChat 在线聊天工具

from tkinter.scrolledtext import *  # 滚动条模块
from tkinter.filedialog import *  # 打开文件窗口模块
from tkinter.ttk import *  # Windows风格界面模块
import os  # 系统底层函数模块
import os.path
import time  # 时间模块
import socket  # Socket网络模块
import base64  # Base64编码模块
import _thread  # 多线程模块
import configparser  # 设置文件模块


class ChatClient(Frame):
    # 初始化程序
    def __init__(self, master):
        Frame.__init__(self, master)
        self.root = master
        self.root.bind_all("<F1>", self.show_settings)  # 绑定 F1 键
        self.getConfig()  # 加载配置文件
        self.chatServerSoc = None  # 本地服务端SOCKET对象
        self.serverStatus = 0  # 服务端设置状态，1为已设置
        self.chatBuffSize = 1024  # 消息缓冲区大小
        self.fileBuffSize = 5120  # 文件缓冲区大小
        self.fileServerPort = 11251  # 文件传输端口
        self.allClients = {}  # 客户端列表
        self.serverIP = "0.0.0.0"  # 监听本机全部 IPV4 地址

        #################################################################################

        # 设置窗口标题和大小
        self.root.title("nP Chat")  # 设置窗口标题
        self.root.resizable(width=False, height=False)  # 禁止更改窗口大小

        # 设置窗口页边距
        parent_frame = Frame(self.root)
        parent_frame.grid(padx=10, pady=10, stick=E + W + N + S)

        # 绘制地址设置部分
        setting_group = Frame(parent_frame)
        server_label = Label(setting_group, text="用户名: ")  # 用户名标签
        self.name_var = StringVar()  # 用户名输入文本框
        self.name_var.set("")
        self.nameField = Entry(setting_group, width=20, textvariable=self.name_var)
        self.nameField.bind("<Return>", self.handleSetServer)
        self.serverPortVar = StringVar()  # 服务端端口设置文本框
        self.serverPortVar.set("8090")
        self.serverPortField = Entry(setting_group, width=5, textvariable=self.serverPortVar)
        self.serverPortField.bind("<Return>", self.handleSetServer)
        self.serverSetButton = Button(setting_group, text="设置", width=10, command=self.handleSetServer)  # 设置服务端按钮
        add_client_label = Label(setting_group, text="     添加好友: ")  # 添加好友标签
        self.clientIPVar = StringVar()  # 客户端IP设置文本框
        self.clientIPVar.set("127.0.0.1")
        client_ip_field = Entry(setting_group, width=14, textvariable=self.clientIPVar)
        client_ip_field.bind("<Return>", self.handleAddClient)
        self.clientPortVar = StringVar()  # 客户端端口设置文本框
        self.clientPortVar.set("8090")
        client_port_field = Entry(setting_group, width=5, textvariable=self.clientPortVar)
        client_port_field.bind("<Return>", self.handleAddClient)
        client_add_button = Button(setting_group, text="添加", width=10, command=self.handleAddClient)  # 添加客户端按钮
        server_label.grid(row=0, column=0)  # 显示各种对象于框架中
        self.nameField.grid(row=0, column=1)
        self.serverPortField.grid(row=0, column=2)
        self.serverSetButton.grid(row=0, column=3, padx=5)
        add_client_label.grid(row=0, column=4)
        client_ip_field.grid(row=0, column=5)
        client_port_field.grid(row=0, column=6)
        client_add_button.grid(row=0, column=7, padx=5)

        # 绘制聊天记录部分和好友列表部分
        read_chat_group = Frame(parent_frame)
        self.receivedChats = ScrolledText(read_chat_group, bg="white", width=60, height=25, state=DISABLED)  # 聊天记录文本框
        self.friends = Listbox(read_chat_group, bg="white", width=25, height=25, selectmode=MULTIPLE)  # 好友列表框
        self.receivedChats.grid(row=0, column=0, sticky=W + N + S, padx=(0, 10))
        self.friends.grid(row=0, column=1, sticky=E + N + S)

        # 绘制消息发送部分
        write_chat_group = Frame(parent_frame)
        self.chatVar = StringVar()  # 发送消息文本框
        self.chatField = Entry(write_chat_group, width=67, textvariable=self.chatVar)
        self.chatField.bind("<Return>", self.handle_send_chat)
        self.sendChatButton = Button(write_chat_group, text="发送消息", width=8, command=self.handle_send_chat)  # 消息发送按钮
        self.sendFileButton = Button(write_chat_group, text="发送文件", width=8, command=self.handle_send_file)  # 文件发送按钮
        self.chatField.grid(row=0, column=0, sticky=W)
        self.sendChatButton.grid(row=0, column=1, padx=5)
        self.sendFileButton.grid(row=0, column=2, padx=5)

        # 绘制状态栏
        self.statusLabel = Label(parent_frame, text="本机IP：%s    F1 键呼出设置窗口" % socket.gethostbyname(socket.gethostname()))

        # 显示框架于屏幕上
        setting_group.grid(row=0, column=0)
        read_chat_group.grid(row=1, column=0)
        write_chat_group.grid(row=2, column=0, pady=10)
        self.statusLabel.grid(row=3, column=0)

        # 设置选择文件对话框
        self.file_opt = self.fileDialogOptions = {}
        self.fileDialogOptions["title"] = "文件发送"  # 打开文件对话框标题

    # 显示设置对话框
    def show_settings(self, event=None):
        self.root.unbind_all("<F1>")  # 禁用F1键，防止打开多个设置窗口
        self.setting_dialog = Toplevel(self.root)  # 创建设置窗口
        self.setting_dialog.protocol("WM_DELETE_WINDOW", self.saveConfig)  # 关闭窗口时保存
        self.setting_dialog.title("设置 ")  # 设置窗口标题
        setting_frame = Frame(self.setting_dialog)
        setting_frame.grid(padx=10, pady=10, stick=E + W + N + S)

        # 绘制响铃选项框架
        ringFrame = Frame(setting_frame)
        ringLabel = Label(ringFrame, text="有新消息时响铃")  # 响铃标签
        ringTrueButton = Radiobutton(ringFrame, text="响铃", value="1", variable=self.ringVar)  # 响铃单选按钮
        ringFalseButton = Radiobutton(ringFrame, text="不响铃", value="0", variable=self.ringVar)  # 不响铃单选按钮
        ringLabel.grid(row=0, column=0)
        ringTrueButton.grid(row=1, column=0, padx=20, stick=W)
        ringFalseButton.grid(row=2, column=0, padx=20, stick=W)

        # 绘制文件打开选项框架
        fileOpenFrame = Frame(setting_frame)
        fileOpenLabel = Label(fileOpenFrame, text="接收到新文件时自动打开")  # 打开文件标签
        fileOpenTrueButton = Radiobutton(fileOpenFrame, text="自动打开", value="1", variable=self.fileOpenVar)
        fileOpenFalseButton = Radiobutton(fileOpenFrame, text="不自动打开", value="0", variable=self.fileOpenVar)
        fileOpenLabel.grid(row=0, column=0)
        fileOpenTrueButton.grid(row=1, column=0, padx=20, stick=W)
        fileOpenFalseButton.grid(row=2, column=0, padx=20, stick=W)

        # 绘制保存按钮
        settingSaveButton = Button(setting_frame, text="保存", command=self.saveConfig)  # 保存按钮

        # 显示框架于屏幕上
        ringFrame.grid(row=0, column=0)
        fileOpenFrame.grid(row=1, column=0, pady=10)
        settingSaveButton.grid(row=2, column=0)

    # 读取配置文件，当配置文件不存在时，创建它
    def getConfig(self):
        self.config = configparser.ConfigParser()
        self.config.read("npConfig.ini")  # 配置文件名
        try:
            # 配置文件不存在时创建它
            self.config.add_section("Config")
            self.ringVar = StringVar()  # 收到消息时响铃
            self.ringVar.set("1")
            self.fileOpenVar = StringVar()  # 收到文件时打开
            self.fileOpenVar.set("1")
            self.config.set("Config", "ring", "1")  # 收到消息时响铃
            self.config.set("Config", "fileOpen", "1")  # 收到文件时打开
            self.config.write(open("npConfig.ini", "w"))
            return
        except:
            # 读取配置文件
            self.ringVar = StringVar()  # 收到消息时响铃
            self.ringVar.set(self.config.get("Config", "ring"))
            self.fileOpenVar = StringVar()  # 收到文件时打开
            self.fileOpenVar.set(self.config.get("Config", "fileopen"))
            return

    # 保存配置文件，由 WM_DELETE_WINDOW 和 settingSaveButton 触发
    def saveConfig(self, event=None):
        self.config.set("Config", "ring", self.ringVar.get())  # 收到消息时响铃
        self.config.set("Config", "fileOpen", self.fileOpenVar.get())  # 收到文件时打开
        self.config.write(open("npConfig.ini", "w"))
        self.setting_dialog.destroy()  # 关闭设置窗口
        self.root.bind_all("<F1>", self.show_settings)  # 启用F1键
        return

    # 设置本地服务端地址，由 serverSetButton 和附近的 <Return> 触发
    def handleSetServer(self, event=None):
        try:
            # 检测并提示部分错误
            if self.name_var.get() == "":  # 检测是否输入用户名
                self.set_status("未输入用户名")
                return
            if int(self.serverPortVar.get()) == self.fileServerPort:  # 检测端口是否被占用
                self.set_status("该端口被占用")
                return

            # 调用 listenClients()， receiveFiles()在服务端启动监听
            chatServerAddr = (self.serverIP.replace(" ", ""), int(self.serverPortVar.get().replace(" ", "")))
            self.chatServerSoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chatServerSoc.bind(chatServerAddr)
            self.chatServerSoc.listen(5)
            _thread.start_new_thread(self.listenClients, ())  # 监听消息传输
            _thread.start_new_thread(self.receiveFiles, ())  # 监听文件传输

            # 设置服务端状态
            self.set_status("正在监听 %s:%s" % chatServerAddr)  # 设置状态栏信息
            self.serverStatus = 1  # 设置服务器状态

            # 禁用服务端设置按钮
            self.serverSetButton.config(state=DISABLED)  # 禁用服务器设置按钮
            self.nameField.config(state=DISABLED)  # 禁用用户名输入文本框
            self.serverPortField.config(state=DISABLED)  # 禁用服务器端口设置文本框
        except:
            self.set_status("设置服务端错误")
        return

    # 服务端接收通信请求，调用 handleClientMessages()接收消息，由 handleSetServer()调用
    def listenClients(self):
        try:
            while 1:
                clientsoc, clientaddr = self.chatServerSoc.accept()  # 开始接收通信请求
                _thread.start_new_thread(self.handle_client_messages,(clientsoc, clientaddr))
                self.set_status("已连接 %s:%s" % clientaddr)  # 设置状态栏信息
            self.chatServerSoc.close()
        except:
            self.set_status("设置服务端错误")
        return

    # 启动文件传输端口监听，接收文件，由 handleSetServer()调用
    def receiveFiles(self):
        # 设置文件传输服务端
        self.fileServerSoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.fileServerSoc.bind(("0.0.0.0", self.fileServerPort))
        self.fileServerSoc.listen(5)

        while 1:
            # 接收文件信息
            fileRecvSoc, fileRecvAddr = self.fileServerSoc.accept()
            recvFilename, recvUsername, fileSize = ((fileRecvSoc.recv(self.fileBuffSize)).decode("utf-8")).split("|")
            fileRecvSoc.close()

            # 显示接收文件状态
            self.set_status("正从 %s 处接收文件 %.50s (%s)" % (recvUsername, recvFilename, fileSize))

            # 创建文件
            recvFileDir = os.getcwd() + "\\" + recvFilename  # 文件路径
            recvFile = open(recvFileDir + ".npt", "wb")

            # 接收并写入文件
            fileRecvSoc, fileRecvAddr = self.fileServerSoc.accept()  # 建立连接
            recvFileContent = fileRecvSoc.recv(self.fileBuffSize)
            while recvFileContent:
                recvFile.write(recvFileContent)
                recvFileContent = fileRecvSoc.recv(self.fileBuffSize)
            recvFile.close()
            fileRecvSoc.close()

            try:
                # 重命名文件。如果文件已经存在，显示“文件已存在”
                os.rename(recvFileDir + ".npt", recvFileDir)

                # 显示接收文件状态
                self.add_chat(
                    time.strftime("%H:%M:%S ") + "成功从 %s 处接收文件 %s (%s)" % (recvUsername, recvFilename, fileSize))
                self.set_status("接收文件成功")

                # 检测设置
                if self.ringVar.get() == "1":  # 检测设置并响铃
                    print("\a")
                if self.fileOpenVar.get() == "1":  # 检测设置并打开文件
                    os.system("\"" + recvFileDir + "\"")
            except:
                self.set_status("文件 %s 已存在" % recvFilename)

    # 连接对方服务端，调用 handleClientMessages()接收消息，由 clientAddButton 触发
    def handleAddClient(self, event=None):
        # 检测是否已经设置本地服务端地址
        if self.serverStatus == 0:
            self.set_status("未设置本地地址")
            return

        # 连接对方服务端
        try:
            clientaddr = (self.clientIPVar.get().replace(" ", ""), int(self.clientPortVar.get().replace(" ", "")))
            clientsoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientsoc.connect(clientaddr)
            clientsoc.send(bytes(self.name_var.get() + "|", "utf-8") + base64.b64encode(
                bytes(self.name_var.get(), "utf-8")))  # 发送用户名
            _thread.start_new_thread(self.handle_client_messages, (clientsoc, clientaddr))  # 接收消息
            self.set_status("已连接 %s:%s" % clientaddr)  # 显示状态
        except:
            self.set_status("连接错误")

    # 建立连接，调用addClient()添加好友，开始接收消息。由 listenClients()， handleAddClient()调用
    def handle_client_messages(self, clientsoc, clientaddr):
        while 1:
            # 接收消息并显示
            data = (clientsoc.recv(self.chatBuffSize)).decode("utf-8")

            # 判断消息是否为传输的用户名
            buf = data.split("|")
            if len(buf) == 2 and buf[1] == bytes.decode(base64.b64encode(bytes(buf[0], "utf-8"))):  # 判断消息是否为传输的用户名
                if buf[0] not in self.allClients.values():
                    self.add_client(clientsoc, buf[0])  # 添加好友
                    clientsoc.send(bytes(self.name_var.get() + "|", "utf-8") + base64.b64encode(
                        bytes(self.name_var.get(), "utf-8")))  # 回传用户名
            else:
                self.add_chat(data)  # 添加消息

            # 检测设置并响铃
            if self.ringVar.get() == "1":
                print("\a")

        # 断开连接，调用 removeClient()删除好友
        self.remove_client(clientsoc)
        clientsoc.close()
        self.set_status("连接 %s:%s 断开" % clientaddr)  # 显示状态

    # 发送消息，由 sendChatButton 触发
    def handle_send_chat(self, event=None):
        # 检测是否已经设置服务端地址
        if self.serverStatus == 0:
            self.set_status("未设置本地地址")
            return

        # 判断消息发送框是否为空
        if self.chatVar.get() == "":
            return

        # 判断选择好友是否为空
        if not self.get_selected_soc():
            self.set_status("未选择好友")
            return

        # 为选定好友发送消息
        msg = self.name_var.get() + time.strftime(" %H:%M:%S:\n") + self.chatVar.get()  # 组装消息内容
        self.add_chat(msg)  # 添加消息至消息记录文本框
        for client in list(self.get_selected_soc()):  # 未选定好友发送消息
            client.send(bytes(msg, "utf-8"))
        self.chatVar.set("")  # 清空消息键入文本框
        self.set_status("")  # 清空状态栏

    # 获取 listbox 中已选择的socket对象
    def get_selected_soc(self):
        soclist = []
        try:
            for key, value in self.allClients.items():  # 遍历客户端列表
                if value in self.friends.selection_get():  # 如果用户名被选中
                    soclist.append(key)  # 将 soc 加入列表中
            return soclist
        except:
            return

    # 发送文件，由 sendFileButton 触发
    def handle_send_file(self):
        self.set_status("正在传输文件")

        # 读取文件
        try:
            file_dir = askopenfilename(**self.file_opt)  # 请求文件路径
            file_to_send = open(file_dir, "rb")
            data = file_to_send.read()  # 读取文件内容
            file_to_send.close()
            file_name = os.path.basename(file_dir)  # 获取文件名
        except:
            self.set_status("文件选择错误")
            return

        # 为选定好友传输文件
        try:
            for socToSend in self.get_selected_soc():
                # 发送文件名、服务端名称、文件大小
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                IPToSend, portToSend = socToSend.getpeername()
                soc.connect((IPToSend, self.fileServerPort))  # 连接至客户端
                soc.send(bytes(file_name + "|" + self.name_var.get() + "|" + self.get_file_size(file_dir), "utf-8"))
                soc.close()
                time.sleep(3)

                # 发送文件内容
                soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                soc.connect((IPToSend, self.fileServerPort))  # 连接至客户端
                soc.sendall(data)  # 发送文件内容
                soc.close()

                # 设置状态
                self.add_chat(time.strftime("%H:%M:%S ") + "已发送 %s 至 %s " % (file_name, self.allClients[socToSend]))
                self.set_status("发送文件成功")  # 设置状态栏信息
            return
        except:
            self.set_status("文件传输失败")  # 提示文件传输失败
            return

    # 向聊天记录框中添加消息
    def add_chat(self, msg):
        self.receivedChats.config(state=NORMAL)  # 允许编辑消息记录文本框
        self.receivedChats.insert("end", msg + "\n\n")  # 在消息记录末尾添加消息
        self.receivedChats.yview(MOVETO, 1)  # 自动向下翻页
        self.receivedChats.config(state=DISABLED)  # 禁止编辑消息记录文本框

    # 向 allClients 字典中添加项，向好友列表中添加项
    def add_client(self, client_soc, client_name):
        self.allClients[client_soc] = client_name  # 向 allClients 字典中添加项
        self.friends.insert(END, "%s" % client_name)  # 向好友列表中添加项

    # 从 allClients 字典中删除项，从好友列表中删除项
    def remove_client(self, client_soc):
        try:
            for i in range(0, self.friends.size()):  # 从 allClients 字典中删除项
                if self.friends.get(i) == self.allClients[client_soc]:
                    self.friends.delete(i)
                    break
            del self.allClients[client_soc]  # 从好友列表中删除项
        except:
            return

    # 获取文件大小
    @staticmethod
    def get_file_size(file_dir):
        file_size = os.path.getsize(file_dir)  # 获取文件大小
        if file_size < 1024:  # 以 B 为单位输出
            return "%dB" % file_size
        elif file_size < 1024 ** 2:  # 以 KB 为单位输出
            return "%.2fKB" % (file_size / 1024.)
        elif file_size < 1024 ** 3:  # 以 MB 为单位输出
            return "%.2fMB" % (file_size / 1024. / 1024.)
        elif file_size < 1024 ** 4:  # 以 GB 为单位输出
            return "%.2fGB" % (file_size / 1024. / 1024. / 1024.)

    # 设置状态栏文字
    def set_status(self, msg):
        self.statusLabel.config(text=msg)
        print(msg)


if __name__ == "__main__":
    root = Tk()
    app = ChatClient(root)
    root.mainloop()