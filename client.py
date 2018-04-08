import optparse
import os
import sys
import cons
import time
import socket
import struct
__version__ = '0.0.1'

def main():
    actState("DISCONNECTED")
    register()

#FASE DE REGISTRE
#PROCES D'ENREGISTRAMENT
def register():
    global rndnum
    reply = ""

    debugMode("Client passa a NOT_SUBSCRIBED")
    actState("NOT_SUBSCRIBED")
    createSock()
    debugMode("Create Socket UDP")
    treatDataFile()
    debugMode("Lectura del fitxer de dades del client")

    regPDU = definePDU(cons.PDU_FORM,cons.SUBS_REQ, cons.DEF_RND, name + ',' + situation)
    debugMode("Inici del proces de registre")
    reply = registerloop(regPDU)
    debugMode("Proces de registre finalitzat")
    #rndnum = reply[3]
    replyProcess(reply)

#MOSTRA L'ESTAT DEL CLIENT
def actState(st):
    global state
    #mostra els canvis d'estat
    state = st
    print time.strftime('%X') + " Client passa a l'estat: " + state

#LLEGIR DEL FITXER
def readFile(fileToRead, i):
    #lectura del fitxer i retorn del contingut
    try:
        f = open(fileToRead, "r")

        lines = f.readlines()
        f.close()

        return lines
    except IOError:
        print time.strftime('%X') + " No es pot localitzar el fitxer"
        if i == 1:
            sys.exit()
        else:
            return "null"

#BUCLE PER ENREGISTRAMENT
def registerloop(regPDU):
    num_packs = 1
    seq_num = 1
    t = 2

    #intentar registrar-se mentre no s'arribi al nombre maxim d'intents
    while seq_num <= cons.MAX_SEQ:
        try:
            debugMode("Intent de registre " + str(seq_num))
            debugMode("Packet numero " + str(num_packs))
            return regTry(regPDU, t)

        except socket.timeout:
        #si no es realitza el registre modifiquem el temps de enviament del
        #seguent intent de registre en funcio del nombre de paquets enviats
            if num_packs == 1:
                t = 2

            if num_packs >= 3 and t != cons.MAX_TIME:
                t = t + 2

            elif num_packs == cons.MAX_PACK:
                t = t + 5
                num_packs = 1
                seq_num = seq_num + 1

            num_packs = num_packs + 1

    return ""

#ENVIAMENT PDU PER REGISTRE
def regTry(regPDU, t):
    global socudp, state, options, server, srvUDP, recPort
    #s'intenta fer un registre
    recPort = socudp.getsockname()[1]
    actState("WAIT_ACK_SUBS")
    #enviem la nostra PDU i establim un temps per esperar la resposta
    socudp.sendto(regPDU, (server, int(srvUDP)))
    socudp.settimeout(t)
    #retornem la resposta si l'hem rebut, en cas contrari es llanca una
    #exepcio que sera agafada per la funcio "registerloop"
    return struct.unpack(cons.PDU_FORM,socudp.recvfrom(recPort)[0])

#MODEDEBUG
def debugMode(toPrint):
    if options.verbose == True:
        print time.strftime('%X') + ' ' + "[DEBUG]->" + ' ' + toPrint


#TRACTAMENT DADES LLEGIDES
def treatDataFile():
    global name, situation, elemntslst, mac, localTCP, server, srvUDP
    #lectura del fitxer i recollida de dades necessaries.
    name, situation, elemnts, mac, localTCP, server, srvUDP = readFile(options.client,1)
    name = name.split('=')[1].strip()
    situation = situation.split('=')[1].strip()
    elemnts = elemnts.split('=')[1].strip()
    elemntslst = elemnts.split(';')
    mac = mac.split('=')[1].strip()
    localTCP = localTCP.split('=')[1].strip()
    server = server.split('=')[1].strip()
    srvUDP = srvUDP.split('=')[1].strip()

#FUNCIONS UTILITZADES EN TOTES LES FASES
#DEFINEIX LA PDU A UTILITZAR
def definePDU(form, sign, random, data):
    global mac
    #crea una PDU amb les dades rebudes per parametre
    debugMode("Dades a enviar:")
    debugMode("Tipus Paquet: " + str(sign) + " MAC: " + mac + " Numero aleatori: " + str(random) + " Dades: " + data)
    return struct.pack(form, sign, mac, random, data)

#CREACIO DEL SOCSKET
def createSock():
    global socudp

    #creacio i assignacio del socket a un port
    socudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socudp.bind(("", 0))

#TRACTAMENT DE RESPOSTA DE REGISTRE
def replyProcess(reply):
    #tractem la resposta rebuda per part del servidor en funcio del tipus de paquet
    #que haguem rebut
    if reply == "":
        print time.strftime("%X") + " No s'ha pogut contactar amb el servidor"
        closeConnection()

    elif reply[0] == cons.SUBS_ACK:
        actState("CONNECTED")
        #en cas de que el registre sigui correcte ens disposem a distribuir el
        #treball de mantenir la comunicacio i la recepcio de comandes
        distributeWork(reply)

    elif reply[0] == cons.SUBS_NACK:
        print time.strftime("%X") + " Denegacio de Registre"
        actState("NOT_SUBSCRIBED")
        closeConnection()

    elif reply[0] == cons.SUBS_REJ:
        print time.strftime("%X") +" "+ reply[4].rstrip('\n')
        actState("NOT_SUBSCRIBED")
        closeConnection()

    elif reply[0] == cons.INFO_ACK:
        print time.strftime("%X") + " Error de Protocol"
        closeConnection()
    else:
        print time.strftime("%X") + " Estat Desconegut"
        closeConnection()

#DIVISIO DE TREABALL PER RECEPCIO DE TECLAT I TRACTAMENT ALIVES
def distributeWork(reply):
    global pid
    debugMode("Registre Correcte")
    debugMode("Creacio de proces fill per a rebre instruccions per teclat")
    pid = os.fork()
    #distribuim el treball a realitzar
    #la rebuda de comandes sera realitzada per el "fill" mentre que el manteniment
    #de la conexio el realitzara el "pare"
    if pid == 0:
        debugMode("Proces fill preparat per a rebre instruccions per teclat")
        KeyboardCommand(reply)

    else:
        debugMode("Proces pare preparat per iniciar el manteniment de comunicacions")
        while True:
            i = i+1
        #AliveTreatment(reply)

#TANCA CONEXIO UDP
def closeConnection():
    global socudp
    #tancament de la coexio
    actState("DISCONNECTED")
    socudp.close()

#FASE DE RECECPCIO DE COMANDES
def KeyboardCommand(reply):
    #recepcio de comandes fins que s'introdueixi la comanda quit
    debugMode("Iniciant espera de comandes")
    while True:
        try:
            #lectura de consola
            com = raw_input("")

            #tancament de tots els processos en cas de quit
            if com == cons.QUIT:
                debugMode("Rebut quit, finalitzant client")
                while True:
                    os.kill(os.getppid(),signal.SIGTERM)
                    #enviament de configuracio en cas de send
            elif com == cons.STAT:
                debugMode("Rebut stat")
                global name, situation, elemntslst, mac, localTCP, server, srvUDP
                print "MAC: " + mac
                print "Nom: " + name
                print "Situacio: " + situation
                print "Elementslst: "
                for i in elemntslst:
                    print i
            else:
                print time.strftime('%X') + " Commanda Incorrecta"

        except KeyboardInterrupt:
            while True:
                os.kill(os.getppid(),signal.SIGTERM)
        except socket.error:
            pass
        except:
            #tancament en cas de fallada de recepcio de comandes
            while True:
                os.kill(os.getppid(),signal.SIGTERM)

if __name__ == '__main__':
    #parseig de les comandes rebudes a la hroa de la crida
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), usage=globals()["__doc__"], version=__version__)
    parser.add_option('-c', '--client', action='store', default='client.cfg', help='-c <nom_arxiu>')
    parser.add_option('-f', '--file', action='store', default='boot.cfg', help='-f <nom_arxiu>')
    parser.add_option('-d', '--debug', action='store_true', dest='verbose', default=False)
    (options, args) = parser.parse_args()
    main()
