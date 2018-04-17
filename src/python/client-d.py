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


# TRACTAMENT DEL SENYAL
def handler(signum, frame):
    global pid, state, socudp
    # tractament del senyal kill
    os.kill(pid, signal.SIGKILL)
    state = utilities.closeConnection(socudp, state)
    sys.exit()


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
    elements = (localTCP, ';'.join(elemntslst))
    data = ','.join(elements)
    comPDU = utilities.definePDU(options.verbose, cons.PDU_FORM,
                                 cons.SUBS_INFO, mac, rndnum, data)
    socudp.sendto(comPDU, (server, int(srvUDP)))
    state = utilities.actState("WAIT_ACK_INFO")
    reply = struct.unpack(cons.PDU_FORM, socudp.recvfrom(recPort)[0])
    replyProcess(reply)


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
        # helloTreatment(reply)
        sys.exit()


# TRACTAMENT DE RESPOSTA DE REGISTRE
def replyProcess(reply):
    global state, socudp, rndnum
    # tractem la resposta rebuda per part del servidor en funcio del tipus
    # de paquet que haguem rebut

    if reply == "":
        print time.strftime("%X") + " No s'ha pogut contactar amb el servidor"
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.SUBS_ACK:
        # en cas de que el registre sigui correcte ens disposem a distribuir el
        # treball de mantenir la comunicacio i la recepcio de comandes
        time.sleep(1)
        sendSubsInfo()

    elif reply[0] == cons.SUBS_NACK:
        print time.strftime("%X") + " Denegacio de Registre"
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)

    elif reply[0] == cons.SUBS_REJ:
        print time.strftime("%X") + " " + reply[3].rstrip('\n')
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)
        time.sleep(2)
        register()

    elif reply[0] == cons.INFO_ACK:
        print time.strftime("%X") + " Rebut INFO_ACK"
        distributeWork(reply)
    else:
        print time.strftime("%X") + " Estat Desconegut"
        state = utilities.closeConnection(socudp, state)


# ENVIAMENT PDU PER REGISTRE
def regTry(regPDU, t):
    global socudp, state, options, server, srvUDP, recPort
    # s'intenta fer un registre
    recPort = socudp.getsockname()[1]
    # enviem la nostra PDU i establim un temps per esperar la resposta
    utilities.debugMode("Enviant packet de registre", options.verbose)
    socudp.sendto(regPDU, (server, int(srvUDP)))
    socudp.settimeout(t)
    state = utilities.actState("WAIT_ACK_SUBS")
    # retornem la resposta si l'hem rebut, en cas contrari es llanca una
    # exepcio que sera agafada per la funcio "registerloop"
    unpacked = struct.unpack(cons.PDU_FORM, socudp.recvfrom(recPort)[0])
    print unpacked
    return unpacked


# BUCLE PER ENREGISTRAMENT
def registerloop(regPDU):
    global state
    num_packs = 1
    seq_num = 1
    t = 2

    # intentar registrar-se mentre no s'arribi al nombre maxim d'intents
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


# PROCES D'ENREGISTRAMENT
def register():
    global rndnum, state, socudp, name, situation, elemntslst, mac, localTCP
    global server, srvUDP, server_mac
    reply = ""
    socudp = utilities.createSock()
    utilities.debugMode("Create Socket UDP", options.verbose)

    name, situation, elemntslst, mac, localTCP, server, srvUDP = \
        utilities.treatDataFile(options.client)

    utilities.debugMode("Lectura del fitxer de dades del client",
                        options.verbose)
    data = name + ',' + situation
    regPDU = utilities.definePDU(options.verbose, cons.PDU_FORM, cons.SUBS_REQ,
                                 mac, cons.DEF_RND, data)

    utilities.debugMode("Inici del proces de registre", options.verbose)
    reply = registerloop(regPDU)
    utilities.debugMode("Proces de registre finalitzat", options.verbose)
    utilities.debugMode("Paket Rebut => Tipus: " + str(reply[0]) + " MAC: " +
                        reply[1] + " Random: " + reply[2] + " Dades: " +
                        reply[3].rstrip('\00')+'\0', options.verbose)
    rndnum = reply[2].rstrip('\x00')

    replyProcess(reply)


def main():
    global state
    state = utilities.actState("NOT_SUBSCRIBED")
    register()


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
