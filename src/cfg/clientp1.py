import sys, os, traceback, optparse
import time, datetime
import socket, select
import struct, signal

# ESTATS
DISCONNECTED = 0xa0
NOT_SUBSCRIBED = 0xa1
WAIT_ACK_SUBS = 0xa2
WAIT_INFO = 0xa3
WAIT_ACK_INFO = 0xa4
SUBSCRIBED = 0xa5
SEND_HELLO = 0xa6

# TIPUS DE PAQUETS SUBSCRIPCIO
SUBS_REQ = 0x00
SUBS_ACK = 0x01
SUBS_REJ = 0x02
SUBS_INFO = 0x03
INFO_ACK = 0x04
SUBS_NACK = 0x05

# MANTENIR LA COMUNICACIO
HELLO = 0x10
HELLO_REJ = 0x11

# ENVIAR I REBRE DADES DEL SERVIDOR
SEND_DATA = 0x20
SET_DATA = 0x21
GET_DATA = 0x22
DATA_ACK = 0x23
DATA_NACK = 0x24
DATA_REJ = 0x25

# global variables
#status = "" # client status

server_mac = ""

server_tcp = ""
random_num = ""
ip = 0
global server_ip
server_ip = ""

d = 0
pid = 0

#auxiliar functions
def dict_to_list(elems):
    list = []
    for elem in elems:
        list.append(elem)
    return list
def list_to_str(list):
    for i in list:
        s = ";".join(list)
    return s
def data_left(data1, data2):
    st = ""
    s = str(data1) + str(data2) # + ','
    for i in range(79 - len(s)): #80
        st += " "
    return st

def create_package_udp(kind, mac, random_num, data):
    package = [kind, mac, random_num, data]
    pdu = PDU_udp(package)
    return pdu

class PDU_udp:
	kind = 0x00
	mac = ""
	random_num = ""
	data = ""

	def __init__(self, package):
		self.kind = package[0]
		self.mac = quit_final(package[1])
		self.random_num = quit_final(package[2])
		self.data = quit_final(package[3])



def PDU_udp_package(kind):
	global controler
	data = ""

	if kind == SUBS_REQ:
		data = controler.name + "," + controler.situation + data_left(controler.name, controler.situation)
		pdu = create_package_udp(SUBS_REQ, controler.mac, controler.random_num, data)

	elif kind == SUBS_INFO:

		data = str(controler.tcp_port) + "," + list_to_str(dict_to_list(controler.elements)) + data_left(controler.tcp_port, list_to_str(dict_to_list(controler.elements)))
		pdu = create_package_udp(SUBS_INFO, controler.mac, controler.random_num, data)

	elif kind == HELLO:
		data = controler.name + "," + controler.situation + data_left(controler.name, controler.situation)

		pdu = create_package_udp(HELLO, controler.mac, controler.random_num, data)

	elif kind == HELLO_REJ:
		data = controler.name + "," + controler.situation + data_left(controler.name, controler.situation)

		pdu = create_package_udp(HELLO_REJ, controler.mac, controler.random_num, data)

	return pdu



def open_udp():
    global socket_udp, status, controler

    try:
        socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



    except socket.error as error:
        print "Error en fer el binding del socket UDP."
        print error
        os._exit(1)

    status = NOT_SUBSCRIBED

    print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
    #debug("Obert port UDP per la comunicacio amb el servidor.")

#TODO
def open_tcp():
    global socket_tcp
    #global server_tcp
    global controler

    try:
        #host = socket.gethostbyname(controler.server)
        socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #socket_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_tcp.bind((controler.server,controler.tcp_port))

    except socket.error as error:
        print "Error en fer el binding del socket TCP."
        print error
        os._exit(1)

    socket_tcp.listen(1)
    #debug("Obert port TCP: " + controler.tcp_port + "per la comunicacio amb el servidor")

#TODO
def subscription():

	global server_udp
	global server_tcp
	global status
	global socket_udp
	global socket_tcp
	global server_mac

	t = 1
	n = 7
	p = 3
	q = 3
	u = 2
	req_send = 1
	aux = 2
	seconds = 1

	while status != SUBSCRIBED and status != DISCONNECTED and status != SEND_HELLO:
		check_subs_attempts()
	#server_addr = controler.srv_udp # 316

		while status == NOT_SUBSCRIBED:
			req_send = send_subs_req(req_send)
			status = WAIT_ACK_SUBS
			print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status) + "\n")

		while status == WAIT_ACK_SUBS:
			read, write, excep = select.select([socket_udp], [], [], seconds)
			if len(read) == 0:
				req_send = send_subs_req(req_send)
				if t*aux >= q*t:
					if req_send > n:
						socket_udp.settimeout(seconds)
						req_send = 1
						aux = 2
						seconds = 1
						time.sleep(u)

						restart()
			    		else:
			        		seconds = q*t

				else:
			    		if req_send <= p:
			        		seconds = t

			    		else:
			        		seconds = t * aux
				aux = add_aux(aux,req_send)
			else:
			#Treat first server received package
				res = receive_package()
				if res.kind == SUBS_ACK or res.kind == SUBS_NACK or res.kind == SUBS_REJ:
			    		if res.kind == SUBS_ACK:
						#debug("Rebut paquet [SUBS_ACK]")
						controler.random_num = res.random_num
						server_mac = res.mac
						server_udp = res.data #connectarse al port UDP

						req = PDU_udp_package(SUBS_INFO) ########el problema esta en que fa malament el subsinfo
						send_subs_info(req)
						status = WAIT_ACK_INFO
						print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
			    		elif res.kind == SUBS_NACK:### pag 4
						debug("Rebut paquet [SUBS_NACK]")
						status = NOT_SUBSCRIBED
						req_send = send_subs_req(req_send, req)

			    		else:
						debug("Rebut paquet [SUBS_REJ]")
						restart()
						time.sleep(u)
				else:
					#debug("Rebut paquet diferent")
					restart()
					time.sleep(u)
#####estem aqui######
		while status == WAIT_ACK_INFO:
			res = receive_package() # treat second server package
			#print res.kind#######SUBREJ
			if res.kind == INFO_ACK:
				#debug("Rebut paquet [INFO_ACK]")
				if check_id_server(res.random_num, res.mac, server_mac) != 0 or ip != 0:
					restart()
					time.sleep(u)
				else:
					server_tcp = res.data
					status = SUBSCRIBED
					#debug("Subscripcio del controlador acceptada pel servidor")
					print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
			else:
				#debug("Rebut paquet diferent")
				restart()
				time.sleep(u)

        print str(status)+" -> Estat al HELLO"
    #change port of .cfg
	server_addr = controler.srv_udp
	if status == SUBSCRIBED:
		print " start_connection"
		start_connection()

	if status == SEND_HELLO:
		#debug("Creat proces per enviament periodic de paquets HELLO")
		sub_attempts = 0
		open_tcp()
		pid = os.fork()
		if pid == 0:
		    print " support_connection"
		    support_connection()
		else:
		    print " after_hello"
		    after_hello()
		socket_tcp.close()
		#debug("Tancat socket TCP de la comunicacio amb el servidor")


#TODO
def support_connection(): #arreckar aixo
	global status
	global socket_udp
	v = 2
	s = 3
	#req = PDU_udp
	#res = PDU_udp
	lost = 0
	aux = 0
	start_time = time.time()
	print "Comunicacio periodica establerta"
	start_time = time.time()
	while status == SEND_HELLO:#es queda pillat amb aquet bucle
		read, write, excep = select.select([socket_udp], [], [], v)
		end_time = time.time()
		print start_time
		print end_time
		if (end_time - start_time) >= 2:
            		send_hello()
			time.sleep(v)
		        if len(read) == 0:
		        	lost +=1
            		else:
				lost = 0
				res = receive_package()
				aux = check_id_server(res.random_num, res.mac, server_mac)
				if res.kind != HELLO or aux != 0 or ip != 0:
					if res.kind == HELLO_REJ:
						debug("Rebut paquet [HELLO_REJ]")
						status = NOT_SUBSCRIBED
						print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
						os.kill(os.getppid(), signal.SIGUSR1)
						os._exit(0)

					if aux != 0:
						req = PDU_udp_package(HELLO_REJ)
						send_package(req)
						debug ("Enviat paquet [HELLO_REJ]")

                    			restart()

                		else:
					vr = None
                    			#debug("Rebut paquet [HELLO]")

				start_time = time.time()

		if lost == s:
			#debug("S'han perdut " + lost + "paquets [HELLO] consecutius")
			status = NOT_SUBSCRIBED
			print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
			os.kill(os.getppid(), signal.SIGUSR1)
			os._exit(0)


#TODO
def after_hello():
    if pid > 0:
        while status == SEND_HELLO:
            #712 - 717
            receive_data()
            commands()

        socket_tcp.close()
        debug("Tancat socket TCP per la comunicacio amb el servidor")


def start_connection():
	global status
	r = 2
	v = 2
	#req = PDU_udp
	#res = PDU_udp
	cont = 0
	aux = 0
	time.sleep(v)
	while status == SUBSCRIBED:
		send_hello()
		read, write, excep = select.select([socket_udp],[],[], v)
		if len(read) == 0:
			cont +=1
		else:
			res = receive_package()
			aux = check_id_server(res.random_num, res.mac, server_mac)
			if res.kind != HELLO or aux != 0 or ip != 0:
				if res.kind == HELLO_REJ:
					debug("Rebut paquet [HELLO_REJ]")
				if aux != 0:
					req = PDU_udp_package(HELLO_REJ)
					send_package(req)
					debug("Enviat paquet [HELLO_REJ]")
					restart()
			else:
				status = SEND_HELLO
				print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
		if cont == r:
			debug("El client no ha rebut el primer [HELLO] en " + r + "segons")
			restart()


def send_hello():
    req = PDU_udp_package(HELLO)
    send_package(req)
    #debug("Enviat paquet [HELLO]")

def check_id_server(random_num, mac, server_mac):
    boolean = 1
    if controler.random_num == random_num and server_mac == mac:
        boolean = 0
    elif controler.random_num != random_num:
        print "Num aleatori erroni: " + random_num
    else:
        print "Mac rebuda erronia"

    return boolean

#TODO
def receive_package():
	global server_ip, socket_udp
	try:
		data, addr = socket_udp.recvfrom(struct.calcsize("B13s9s80s")) #pots posar la mida amb numeros dins el recvfrom
		info = struct.unpack("B13s9s80s", data)
		res = PDU_udp(info)
	except socket.error as error:
		print "Error al rebre dades del servidor"
		print error
		os._exit(1)

	return res

    	if server_ip == "":
        	server_ip = addr
    	else:
        	if server_ip != addr:
           		ip = -1



def add_aux(aux, req_send):
    p = 3
    if req_send > p:
        aux +=1
    return aux

def restart():
	global sub_attempts, status
	controler.random_num = "00000000"
	sub_attempts += 1
	status = NOT_SUBSCRIBED
	print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))

def status_string(status):
    st_stat = ""
    if status == DISCONNECTED:
        st_stat = "DISCONNECTED"
    elif status == NOT_SUBSCRIBED:
        st_stat = "NOT_SUBSCRIBED"
    elif status == WAIT_ACK_SUBS:
        st_stat = "WAIT_ACK_SUBS"
    elif status == WAIT_ACK_INFO:
        st_stat = "WAIT_ACK_INFO"
    elif status == SUBSCRIBED:
        st_stat = "SUBSCRIBED"
    elif status == SEND_HELLO:
        st_stat = "SEND_HELLO"
    elif status == WAIT_INFO:
        st_stat = "WAIT_INFO"

    return st_stat

def send_subs_req(req_send):

	req = PDU_udp_package(SUBS_REQ)

	send_package(req)
	#debug("Enviat paquet [SUBS_REQ]")
	req_send +=1
	return req_send

#TODO
def send_package(req):
	global socket_udp, controler
	try:
		s = struct.pack('B', req.kind) + req.mac + '\0' + req.random_num + '\0' + req.data
		socket_udp.sendto(s, (controler.server,controler.srv_udp))
	except:
		print >> sys.stderr, "No puc enviar el paquet"

def send_subs_info(req):
	global socket_udp, controler, server_udp
	try:
		s = struct.pack('B', req.kind) + req.mac + '\0' + req.random_num + '\0' + req.data
		socket_udp.sendto(s, (controler.server, int(server_udp))) ##port udp indicat en les dades del paquet subs_ack
	except:
		print >> sys.stderr, "No puc enviar el paquet"

def check_subs_attempts():
	global status
	o = 3
	if sub_attempts > o:
		status = DISCONNECTED
		print_msg("Controlador: " + controler.name + ", passa a l'estat: " + status_string(status))
		print "Limit de subscripcions superat"
    	else:
        	print "Nou proces de subscripcio " + str(sub_attempts) + status_string(status)

def quit_final(string):
    aux = string.split('\x00')
    return aux[0]

class ClientInfo:
    name = ""
    situation = ""
    elements = {}
    mac = ""
    tcp_port = 0
    server = ""
    srv_udp = 0
    random_num = ""

def readFile(configfile):
    global controler
    global num_elems
    num_elems = 0
    controler = ClientInfo()
    aux = []

    try:
        fd = open(configfile, "r")
        for line in fd:
            if line != "\n":
                line = line.split('=')
                line = line[1].split()
                line = "".join(line)
                aux.append(line)
        fd.close()

        controler.name = aux[0]

        controler.situation = aux[1]

        aux[2] = aux[2].split(';')
        for tok in aux[2]:
            tok = "".join(tok)
            if len(controler.elements) < 10: #Maximum elements = 10
                controler.elements[tok] = None
                num_elems += 1
            else:
                break

        controler.mac = aux[3]
        controler.tcp_port = int(aux[4])
        controler.server = aux[5]
        controler.srv_udp = int(aux[6])
        controler.random_num = "00000000"

    except IOError:
        print "No es pot obrir l'arxiu de configuracio:", configfile
        sys.exit()

def print_msg(msg):
    print datetime.datetime.now().strftime('%H:%M:%S:'), " MSG.   => ", msg,

global sub_attempts
sub_attempts = 1

configfile = "client.cfg"
readFile(configfile)

open_udp()
#debug("Client iniciat : " + controler.name)
while (status != DISCONNECTED):
	if (status == NOT_SUBSCRIBED):
		subscription()
print "salvat"
