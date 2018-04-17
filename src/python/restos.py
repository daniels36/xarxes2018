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


# TRACTAMENT HELLOS
def helloTreatment(reply):
    global socudp, server, srvUDP, rndnum, recPort, pid, state
    # preparacio dels parametres necessaris per al proces de enviament d'HELLOS
    resp = 0
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
                    # debugMode("Paquet rebut: " + "Tipus paquet: " +
                    # str(msg[0]) + " Nom: " + str(msg[1]) + " MAC: " +
                    # str(msg[2]) + " Aleatori " + str(msg[3]) + " Dades: "
                    # + str(msg[4]))
                # si el paquet es un rebug finalitzem proces
                elif msg[0] == cons.HELLO_REJ:
                    utilities.debugMode("Rebut rebuig de paquet",
                                        options.verbose)
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
