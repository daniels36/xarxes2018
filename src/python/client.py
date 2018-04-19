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

global ndnum, state, socudp, name, situation, elemntslst, mac, localTCP
global server, srvUDP, server_mac


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
        # KeyboardCommand(reply)

    else:
        utilities.debugMode("Proces pare preparat per iniciar el \
                  manteniment de comunicacions", options.verbose)
        # helloTreatment(reply)
        sys.exit()


def sendSubsInfo():
    global state
    elements = (localTCP, ';'.join(elemntslst))
    data = ','.join(elements)
    comPDU = utilities.definePDU(options.verbose, cons.PDU_FORM,
                                 cons.SUBS_INFO, mac, rndnum, data)
    print rndnum
    socudp.sendto(comPDU, (server, int(srvUDP)))
    state = utilities.actState("WAIT_ACK_INFO")
    unpacked = struct.unpack(cons.PDU_FORM, socudp.recvfrom(recPort)[0])
    code = unpacked[0]
    data = unpacked[3].rstrip('/x00')
    replyProcess(code, data)


# TRACTAMENT DE RESPOSTA DE REGISTRE
def replyProcess(codi, data):
    global state, socudp, rndnum
    # tractem la resposta rebuda per part del servidor en funcio del tipus
    # de paquet que haguem rebut

    if codi == "":
        print time.strftime("%X") + " No s'ha pogut contactar amb el servidor"
        state = utilities.closeConnection(socudp, state)

    elif codi == cons.SUBS_ACK:
        # en cas de que el registre sigui correcte ens disposem a distribuir el
        # treball de mantenir la comunicacio i la recepcio de comandes
        time.sleep(1)
        sendSubsInfo()

    elif codi == cons.SUBS_NACK:
        print time.strftime("%X") + " Denegacio de Registre"
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)

    elif codi == cons.SUBS_REJ:
        print time.strftime("%X") + " " + data
        state = utilities.actState("NOT_SUBSCRIBED")
        state = utilities.closeConnection(socudp, state)
        time.sleep(2)
        register()

    elif codi == cons.INFO_ACK:
        print time.strftime("%X") + " Rebut INFO_ACK"
        distributeWork(codi)
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
    codi = unpacked[0]
    macServ = unpacked[1].rstrip('/x00')
    rndnum = unpacked[2].rstrip('/x00')
    data = unpacked[3].rstrip('/x00')
    return codi, macServ, rndnum, data


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

    return "", "", "", ""


# PROCES D'ENREGISTRAMENT
def register():
    global rndnum, state, socudp, name, situation, elemntslst, mac, localTCP
    global server, srvUDP, server_mac

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
    code, server_mac, rndnum, data = registerloop(regPDU)
    utilities.debugMode("Proces de registre finalitzat", options.verbose)
    utilities.debugMode("Paket Rebut => Tipus: " + str(code) + " MAC: " +
                        server_mac + " Random: " + rndnum + " Dades: " +
                        data, options.verbose)
    print rndnum
    replyProcess(code, data)


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
