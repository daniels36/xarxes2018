import time
import sys
import socket


# TRACTAMENT DADES LLEGIDES
def treatDataFile(f):
    # lectura del fitxer i recollida de dades necessaries.
    name, situation, elemnts, mac, localTCP, server, srvUDP = readFile(f, 1)

    name = name.split('=')[1].strip()
    situation = situation.split('=')[1].strip()
    elemnts = elemnts.split('=')[1].strip()
    elemntslst = elemnts.split(';')
    mac = mac.split('=')[1].strip()
    localTCP = localTCP.split('=')[1].strip()
    server = server.split('=')[1].strip()
    srvUDP = srvUDP.split('=')[1].strip()

    return name, situation, elemntslst, mac, localTCP, server, srvUDP


# CREACIO DEL SOCSKET
def createSock():

    # creacio i assignacio del socket a un port
    socudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socudp.bind(("", 0))
    return socudp


# MODEDEBUG
def debugMode(toPrint, debug):
    if debug:
        print time.strftime('%X') + ' ' + "[DEBUG]->" + ' ' + toPrint


# MOSTRA CARACTERISIQUES DEL CLIENT PER PANTALLA
def printStat(mac, name, situation, elemntslst):
    print "MAC: " + mac
    print "Nom: " + name
    print "Situacio: " + situation
    print "Elementslst: "
    for item in elemntslst:
        print item


# LLEGIR DEL FITXER
def readFile(fileToRead, i):
    # lectura del fitxer i retorn del contingut
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


# TANCA CONEXIO UDP
def closeConnection(socudp, state):
    state = actState("DISCONNECTED")
    socudp.close()
    return state


# MOSTRA L'ESTAT DEL CLIENT
def actState(st):
    # mostra els canvis d'estat
    state = st
    print time.strftime('%X') + " Client passa a l'estat: " + state
    return state
