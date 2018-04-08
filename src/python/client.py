import optparse
import os
import sys
import cons
import utilities
import time
import socket
import struct
import signal

__version__ = '0.0.1'


def main():
    global state
    state = utilities.actState("DISCONNECTED")
    register()


# FASE DE REGISTRE
# PROCES D'ENREGISTRAMENT
def register():
    global rndnum, state, socudp, name, situation, elemntslst, mac, localTCP
    global server, srvUDP
    reply = ""

    utilities.debugMode("Client passa a NOT_SUBSCRIBED", options.verbose)
    state = utilities.actState("NOT_SUBSCRIBED")
    socudp = utilities.createSock()
    utilities.debugMode("Create Socket UDP")

    name, situation, elemntslst, mac, localTCP, server, srvUDP = \
        utilities.treatDataFile(options.client)

    utilities.debugMode("Lectura del fitxer de dades del client")

    regPDU = definePDU(cons.PDU_FORM, cons.SUBS_REQ, cons.DEF_RND,
                       name + ',' + situation)
    utilities.debugMode("Inici del proces de registre")
    reply = registerloop(regPDU)
    utilities.debugMode("Proces de registre finalitzat")
    rndnum = reply[2]
    replyProcess(reply)


# BUCLE PER ENREGISTRAMENT
def registerloop(regPDU):
    global state
    num_packs = 1
    seq_num = 1
    t = 2

    # intentar registrar-se mentre no s'arribi al nombre maxim d'intents
    state = utilities.actState("WAIT_ACK_SUBS")
    while seq_num <= cons.MAX_SEQ:
        try:
            utilities.debugMode("Intent de registre " + str(seq_num),
                                options.verbose)
            utilities.debugMode("Packet numero " + str(num_packs),
                                options.verbose)
            return regTry(regPDU, t)

        except socket.timeout:
            # si no es realitza el registre modifiquem el temps de enviament
            # del seguent intent de registre en funcio del nombre de paquets
            # enviats
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


# ENVIAMENT PDU PER REGISTRE
def regTry(regPDU, t):
    global socudp, state, options, server, srvUDP, recPort
    # s'intenta fer un registre
    recPort = socudp.getsockname()[1]
    # enviem la nostra PDU i establim un temps per esperar la resposta
    socudp.sendto(regPDU, (server, int(srvUDP)))
    socudp.settimeout(t)
    # retornem la resposta si l'hem rebut, en cas contrari es llanca una
    # exepcio que sera agafada per la funcio "registerloop"
    return struct.unpack(cons.PDU_FORM, socudp.recvfrom(recPort)[0])


# FUNCIONS UTILITZADES EN TOTES LES FASES
# DEFINEIX LA PDU A UTILITZAR
def definePDU(form, sign, random, data):
    global mac
    # crea una PDU amb les dades rebudes per parametre
    utilities.debugMode("Dades a enviar:", options.verbose)
    utilities.debugMode("Tipus Paquet: " + str(sign) + " MAC: " + mac +
                        " Numero aleatori: " + str(random) + " Dades: " + data,
                        options.verbose)

    return struct.pack(form, sign, mac, random, data)


# TRACTAMENT DE RESPOSTA DE REGISTRE
def replyProcess(reply):
    global state, socudp
    # tractem la resposta rebuda per part del servidor en funcio del tipus
    # de paquet que haguem rebut
    if reply == "":
        print time.strftime("%X") + " No s'ha pogut contactar amb el servidor"
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.SUBS_ACK:
        # en cas de que el registre sigui correcte ens disposem a distribuir el
        # treball de mantenir la comunicacio i la recepcio de comandes
        distributeWork(reply)
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.SUBS_NACK:
        print time.strftime("%X") + " Denegacio de Registre"
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.SUBS_REJ:
        print time.strftime("%X") + " " + reply[4].rstrip('\n')
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.INFO_ACK:
        print time.strftime("%X") + " Error de Protocol"
        state = utilities.closeConnection(socudp, state)
    else:
        print time.strftime("%X") + " Estat Desconegut"
        state = utilities.closeConnection(socudp, state)


# DIVISIO DE TREABALL PER RECEPCIO DE TECLAT I TRACTAMENT HELLOS
def distributeWork(reply):
    global pid

    utilities.debugMode("Registre Correcte", options.verbose)
    utilities.debugMode("Creacio de proces fill per a rebre instruccions per \
                        teclat", options.verbose)
    pid = os.fork()
    # distribuim el treball a realitzar
    # la rebuda de comandes sera realitzada per el "fill" mentre que el
    # manteniment de la conexio el realitzara el "pare"
    if pid == 0:
        utilities.debugMode("Proces fill preparat per a rebre instruccions per \
                            teclat", options.verbose)
        KeyboardCommand(reply)

    else:
        utilities.debugMode("Proces pare preparat per iniciar el \
                  manteniment de comunicacions", options.verbose)
        helloTreatment(reply)


# FASE DE MANTENIMENT DE COMUNICACIO
# TRACTAMENT HELLOS
def helloTreatment(reply):
    global socudp, server, srvUDP, rndnum, recPort, pid, state
    # preparacio dels parametres necessaris per al proces de enviament d'HELLOS
    resp = 0
    print situation
    sendSubsInfo()
    time.sleep(3)
    comPDU = definePDU(cons.PDU_FORM, cons.HELLO, rndnum, name + ',' +
                       situation)
    socudp.sendto(comPDU, (server, int(srvUDP)))
    utilities.debugMode("Enviat primer Paquet amb HELLO", options.verbose)
    resp = resp + 1
    timer = time.time()
    first = False
    utilities.debugMode("Iniciant temportizador per a rebre respota de HELLO",
                        options.verbose)

    # recv no bloquejant
    socudp.setblocking(0)
    # enviament de HELLOs
    while True:
        # si el servidor contesta als nostres enviaments continuem enviant
        if resp < 3:
            try:
                # deteccio de finalitzacio
                signal.signal(signal.SIGTERM, handler)
                # recepcio del paquet del servidor
                msg = struct.unpack(cons.PDU_FORM, socudp.recvfrom(recPort)[0])

                resp, timer = sendHello(resp, timer, comPDU)
                # comprovacio del paquet rebut
                if msg[0] == cons.HELLO and cmp(reply[1:4], msg[1:4]) == 0:
                    resp = resp - 1
                    # en cas de resposta al primer HELLO informem del canvi
                    # d'estat
                    if not first:
                        utilities.debugMode("Primer HELLO rebut passem a \
                                            estat HELLO", options.verbose)
                        state = utilities.actState("HELLO")
                        first = True
                        print msg
                    # debugMode("Paquet rebut: " + "Tipus paquet: " +
                    # str(msg[0]) + " Nom: " + str(msg[1]) + " MAC: " +
                    # str(msg[2]) + " Aleatori " + str(msg[3]) + " Dades: "
                    # + str(msg[4]))
                # si el paquet es un rebug finalitzem proces
                elif msg[0] == cons.HELLO_REJ:
                    utilities.debugMode("Rebut rebuig de paquet",
                                        options.verbose)
                    print msg
                    # debugMode("Paquet rebut: " + "Tipus paquet: " +
                    # str(msg[0]) + " Nom: " + str(msg[1]) + " MAC: " +
                    # str(msg[2]) + " Aleatori " + str(msg[3]) + " Dades: "
                    # + str(msg[4]))
                    os.kill(pid, signal.SIGKILL)
                    state = utilities.closeConnection(socudp, state)
                    timedRegister()

                signal.signal(signal.SIGTERM, handler)
            except socket.error:
                signal.signal(signal.SIGTERM, handler)
                resp, timer = sendHello(resp, timer, comPDU)
        # si el servidor no contesta tanquem proces
        else:
            utilities.debugMode("Impossible mantenir comunicacio amb el \
                                servidor", options.verbose)
            os.kill(pid, signal.SIGKILL)
            state = utilities.closeConnection(socudp, state)
            timedRegister()


# INTENT DE REGISTRE TEMPORITZAT
def timedRegister():
    timer = time.time()
    while True:
        if time.time() - timer >= 10:
            register()


# TRACTAMENT DEL SENYAL
def handler(signum, frame):
    global pid, state, socudp
    # tractament del senyal kill
    os.kill(pid, signal.SIGKILL)
    state = utilities.closeConnection(socudp, state)
    sys.exit()


# ENVIAMENT HELLOS
def sendHello(resp, timer, comPDU):
    # enviment d'HELLOs segons temporitzador
    if time.time() - timer >= cons.SND_TM:
        utilities.debugMode("Enviat Paquet HELLO", options.verbose)
        socudp.sendto(comPDU, (server, int(srvUDP)))
        # en cas de enviament increment de numero de enviades per portar
        # control i actualitzacio del temporitzador
        resp = resp + 1
        timer = time.time()

    return resp, timer


# FASE DE RECECPCIO DE COMANDES
def KeyboardCommand(reply):
    global name, situation, elemntslst, mac, localTCP, server, srvUDP
    # recepcio de comandes fins que s'introdueixi la comanda quit
    utilities.debugMode("Iniciant espera de comandes", options.verbose)
    while True:
        try:
            # lectura de consola
            com = raw_input("")

            # tancament de tots els processos en cas de quit
            if com == cons.QUIT:
                utilities.debugMode("Rebut quit, finalitzant client",
                                    options.verbose)
                while True:
                    os.kill(os.getppid(), signal.SIGTERM)
                    # enviament de configuracio en cas de send
            elif com == cons.STAT:
                utilities.debugMode("Rebut stat, es disposa a mostrar la \
                                    configuracio", options.verbose)
                utilities.printStat(mac, name, situation, elemntslst)
            else:
                print time.strftime('%X') + " Commanda Incorrecta"

        except KeyboardInterrupt:
            while True:
                os.kill(os.getppid(), signal.SIGTERM)
        except socket.error:
            pass
        except:
            # tancament en cas de fallada de recepcio de comandes
            while True:
                os.kill(os.getppid(), signal.SIGTERM)


def sendSubsInfo():
    global state
    data = localTCP + ','
    for i in elemntslst:
        data = data + i + ";"

    data = data[:-1]
    print data
    comPDU = definePDU(cons.PDU_FORM, cons.SUBS_INFO, rndnum, data)
    socudp.sendto(comPDU, (server, int(srvUDP)))
    state = utilities.actState("WAIT_ACK_INFO")


if __name__ == '__main__':
    # parseig de les comandes rebudes a la hroa de la crida
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                   usage=globals()["__doc__"],
                                   version=__version__)
    parser.add_option('-c', '--client', action='store',
                      default='../cfg/client.cfg', help='-c <nom_arxiu>')
    parser.add_option('-d', '--debug', action='store_true', dest='verbose',
                      default=False)
    (options, args) = parser.parse_args()
    main()
