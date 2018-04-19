#define _POSIX_SOURCE

#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include <sys/mman.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/wait.h>

#define STATE_DISCON 0
#define STATE_REGIST 1
#define STATE_ALIVE 2

/*REGISTER CODE*/
#define SUBS_REQ 0x00
#define SUBS_ACK 0x01
#define SUBS_REJ 0x02
#define SUBS_INFO 0x03
#define INFO_ACK 0x04
#define SUBS_NACK 0x05

/*ALIVE CODE*/
#define HELLO 0x10
#define HELLO_REJ 0x11

#define LIST "list"
#define QUIT "quit"
#define MAP_ANONYMOUS 0x20
#define NUMCOMPUTERS 100
#define BUFSIZEUDP 103

struct PCREG *registres[NUMCOMPUTERS];
struct PCREG{
  char nomEquip[9];
  char adresaMac[13];
  char IP[9];
  int estat;
  char numAleat[9];
  long timing;
};

struct SERVINFO{
  char nomServ[9];
  char MAC[13];
  char UDP[5];
  char TCP[5];
};

struct PDU_UDP{
  unsigned char tipusPacket;
  char adresaMac[13];
  char numAleat[9];
  char Dades[80];
};


struct SERVINFO serverInfo;
int debug;
int pidWork, pidAlives, pidMsg;
char servFile[30] = "../cfg/server.cfg\0";
char autorized[30] = "../dat/controlers.dat\0";

void modifyPCRegisters(int i, struct sockaddr_in udpRecvAdress);
void readServInfo(struct SERVINFO *serverInfo);
void work(int udpSocket, struct SERVINFO serverInfo, int lines);
void makeUDPPDU(unsigned char sign, struct SERVINFO serverInfo, struct PDU_UDP *sendPDU, char random[], char error[]);
int readPermitedComputers();
int createUDPSocket();
void handler(int sig);
void initializeRandom();
void aliveResponse(int udpSocket, int lines, struct PDU_UDP recvPDU,  struct sockaddr_in udpRecvAdress, struct SERVINFO serverInfo);
void aliveStateChecker(int lines);
void makeErrorPDU(unsigned char sign, char mac[], struct PDU_UDP *sendPDU, char random[], char error[]);
void request(int udpSocket, int lines, struct PDU_UDP recvPDU,  struct sockaddr_in udpRecvAdress, struct SERVINFO serverInfo);
int randomGenerator();

int main(int argc, char *argv[]){
  int udpSocket;
  int lines = 0, i;
  char input[5];
  char estat[12];

  /*Reserva de espai de memória compartida per a la taula de clients*/
  for(i=0;i<NUMCOMPUTERS;i++){
 	  registres[i] = (struct PCREG *)mmap(0, sizeof(*registres[NUMCOMPUTERS]), PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
  }

  /*Parse de linea de comandes*/
  if(argc > 1){
    for(i=1;i < argc; i++){
      /*Parserd mode debug*/
      if(strcmp(argv[i],"-d") == 0){
        debug = 1;
        printf("Mode debug activat\n");
      }
      if(strcmp(argv[i],"-c") == 0){
        /*Parser fitxer arrancada de servidor*/
        if(i+1 < argc){
          sprintf(servFile,"%s", argv[i+1]);
          printf("Realitzat canvi en el fitxer de arrancada de servidor\n");
        }else{
          printf("Detectat -c pero cap nom darrera per defecte el fitxer de arrancada és server.cfg\n");
        }
      }
      if(strcmp(argv[i],"-u") == 0){
        /*Parser fitxer equips autoritzats*/
        if(i+1 < argc){
          sprintf(autorized,"%s", argv[i+1]);
          printf("Realitzat canvi en el fitxer d'equips autoritzats\n");
        }else{
          printf("Detectat -u però cap nom darrera per defecte el fitxer d'equips autoritzats és equips.dat\n");
        }
      }
    }
  }

  /*Lectura del fitxer d'informació del servidor*/
  readServInfo(&serverInfo);
  /*Lectura del fitxer de equips permesos*/

  lines = readPermitedComputers();

  pidWork = fork();
  if(pidWork == 0){
    if(debug == 1){
      printf("[DEBUG] -> Preparat procés per a rebre peticions TCP/UDP\n");
    }
    udpSocket = createUDPSocket();

    printf("[DEBUG] -> Preparat per a rebre regitres:\n");
    work(udpSocket,serverInfo,lines);

    exit(0);
  } else{
    if(debug == 1){
      printf("[DEBUG] -> Preparat procés per a rebre comandes\n");
    }
    while(1){
      scanf("%s",input);

      if(strcmp(input,QUIT) == 0){
        /*Fi del programa*/
        kill(pidWork,SIGTERM);
        return 0;
      }
      else if(strcmp(input,LIST) == 0){
        /*Mostra dels estats dels equips autoritzats*/
        for(i=0;i<lines;i++){
          if(registres[i] -> estat == 0){
            sprintf(estat,"%s","DISCONNECTED");
          }else if(registres[i] -> estat == 1){
            sprintf(estat,"%s","REGISTERED");
          }else if(registres[i] -> estat == 2){
            sprintf(estat,"%s","HELLO");
          }
          printf("Nom Equip: %s\tAdreca Mac: %s\tNumero Aleatori:%s\tIP:%s\tEstat:%s\n",registres[i] -> nomEquip, registres[i] -> adresaMac, registres[i] -> numAleat, registres[i] -> IP, estat);
        }
      }
    }
  }
  return 0;
}


/*Llegeix i agafa les dades del fitxer de informacio del servidor*/
void readServInfo(struct SERVINFO *serverInfo){
  FILE *f;
  char ignore1[8];
  char ignore2[7];
  char ignore3[12];
  char equals[2];
  f = fopen(servFile, "r");
  if(f == NULL){
    printf("El fitxer no existeix");
    exit(0);
  }else{
    /*Llegir la informació del servidor*/
      fscanf(f, "%4s %1s %8s", ignore1, equals, serverInfo -> nomServ);
      fscanf(f, "%3s %1s %12s", ignore2, equals, serverInfo -> MAC);
      fscanf(f, "%8s %1s %5s", ignore3, equals, serverInfo -> UDP);
      fscanf(f, "%8s %1s %5s", ignore3, equals, serverInfo -> TCP);
  }
  fclose(f);
}

/*Lleigeix i agafa les dades del fixer de equips autoritzats*/
int readPermitedComputers(){
  FILE *f;
  int i = 0;
  char coma[2];
  f = fopen(autorized, "r");

  /*Mentres no arribem a fí de fitxer guardem les dades*/
  while(!feof(f)){
    fscanf(f,"%8s %1s %12s", registres[i] -> nomEquip, coma, registres[i] -> adresaMac);
    i++;
  }

  return i-1;
}

/*Creacio del socket UDP*/
int createUDPSocket(){
  int udpSocket;
  struct sockaddr_in udpSockAdress;

  /*creació de socket de protocol UDP*/
  udpSocket = socket(AF_INET,SOCK_DGRAM,0);

  if(udpSocket < 0){
    printf("Error Opening Socket");
  }

  memset((char *)&udpSockAdress, 0, sizeof(udpSockAdress));
  udpSockAdress.sin_family = AF_INET;
  udpSockAdress.sin_addr.s_addr = htonl(INADDR_ANY);
  udpSockAdress.sin_port = htons(2018);

  /*Assignació de socket a adreça*/
  if(bind(udpSocket, (struct sockaddr *)&udpSockAdress, sizeof(udpSockAdress)) < 0){
    perror("bind failed");
    return 0;
  }
  return udpSocket;
}

/*Control de senyal*/
void handler(int sig){
  kill(pidAlives,SIGINT);
  kill(pidMsg,SIGINT);
  exit(0);
}

/*Treball a realitzar*/
void work(int udpSocket, struct SERVINFO serverInfo, int lines){
  int pidAlives, pidMsg ,i;
  long timed;
  char sndrcvFile[10]= "";
  char badPack[] = "Paquet Erroni";
  char noAuto[] = "Equip no autoritzat";
  /*UDP*/
  struct PDU_UDP recvPDU;
  int recvlen;
  struct sockaddr_in udpRecvAdress;
  socklen_t addrlen = sizeof(udpRecvAdress);
  /*UDP*/
  fcntl(udpSocket, F_SETFL, O_NONBLOCK);
  initializeRandom();

  pidAlives = fork();
  if(pidAlives == 0){
    aliveStateChecker(lines);

  }else{
    pidMsg = fork();

    if(pidMsg == 0){
      int pid;

      while(1){
        recvlen = recvfrom(udpSocket, &recvPDU, BUFSIZEUDP, 0, (struct sockaddr *)&udpRecvAdress, &addrlen);

        /*SECCIÓ UDP*/
        if(recvlen > 0){
          /*REGISTRE*/
          /*distribució dels paquets segons el tipus*/
          if(recvPDU.tipusPacket == SUBS_REQ){
            pid = fork();
            /*Procés per gestionar registres*/
            if(pid == 0){
              printf("Rebut registre de %s\n",recvPDU.adresaMac);
              if(debug == 1){
                printf("[DEBUG] -> REBUT: MAC: %s ALEA: %s  DADES: %s\n",recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
              }
              request(udpSocket, lines, recvPDU,  udpRecvAdress, serverInfo);
              exit(0);
            }
          }else if(recvPDU.tipusPacket == SUBS_INFO){
            if(debug == 1){
              printf("[DEBUG] -> REBUT: MAC: %s ALEA: %s  DADES: %s\n",recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
            }
            /*Comprovem si l'equip esta autoritzat i el seu estat es Registered o ALIVE*/
              for(i=0; i<lines ;i++){
                /*Si l'equip es correcte i esta ALIVE enviem HELLO*/
                if(strcmp(registres[i] -> numAleat,recvPDU.numAleat) == 0
                  && strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0
                  && (registres[i] -> estat == STATE_REGIST || registres[i] -> estat == STATE_ALIVE)){
                    //SUBS_INFOOOOOOOOOOOOOOOO;
                  }
              }
            }
          /*Procés per gestionar ALIVES */
          else if(recvPDU.tipusPacket == HELLO){
            pid = fork();
            if(pid == 0){
              aliveResponse(udpSocket, lines, recvPDU, udpRecvAdress, serverInfo);
            }
          }
        }
      }
    }
    while(1){
      signal(SIGTERM,handler);
    }
  }
}

/*Inicialitza el numero aleatori per al equip que es conecta*/
void initializeRandom(){
  int i;
  for( i = 0; i < NUMCOMPUTERS; i++){
    strcpy(registres[i] -> numAleat, "00000000");
  }
}

/*Generador de la PDU de protocol UDP*/
void makeUDPPDU(unsigned char sign,struct SERVINFO serverInfo, struct PDU_UDP *sendPDU, char random[], char dades[]){
  sendPDU -> tipusPacket = sign;
  strcpy(sendPDU -> adresaMac,serverInfo.MAC);
  strcpy(sendPDU -> numAleat,random);
  strcpy(sendPDU -> Dades, dades);
  printf("%lu", sizeof(sendPDU));
  printf("%u, %s, %s, %s\n",sign,serverInfo.MAC, random, dades );
}

/*Comprovacio de estat d'alive*/
void aliveStateChecker(int lines){
  int i;
  int limAlive = 9;
  int firstAlive = 6;
  long now,diff;
  long timed = time(NULL);
  /*Mentres el servidor estigui funcionan comprova dels equips registrats*/
  while(1){
    if(time(NULL)-timed >= 1){
      now = time(NULL);
      for(i = 0;i<lines;i++){
        diff = now - registres[i] -> timing;

        /*Si no s'ha rebut el primer ALIVE en 6 segons(estat del client Registered) es desconecta*/
        if(registres[i] -> estat == 1 && diff > firstAlive){
          registres[i] -> estat = STATE_DISCON;
          registres[i] -> timing = 0;
          printf("%s Desconectat, Alives no rebuts\n",registres[i] -> nomEquip);
        }

        /*Si no s'han rebut un ALIVE en 9 segons(estat del client ALIVE) es desconecta*/
        else if(registres[i] -> estat == 2 && diff > limAlive){
          registres[i] -> estat = STATE_DISCON;
          registres[i] -> timing = 0;
          printf("%s Desconectat, Alives no rebuts\n",registres[i] -> nomEquip);
        }
      }

      timed = time(NULL);
    }
  }
}

/*Resposta als ALIVES REBUTS*/
void aliveResponse(int udpSocket, int lines, struct PDU_UDP recvPDU,  struct sockaddr_in udpRecvAdress, struct SERVINFO serverInfo){
  int i;
  char error[80] = "";
  char alea[9] = "";
  char mac[15] = "";
  struct PDU_UDP sendPDU;
  socklen_t addrlen = sizeof(udpRecvAdress);

  /*Comprovem si l'equip esta autoritzat i el seu estat es Registered o ALIVE*/
  for(i=0; i<lines ;i++){
    /*Si l'equip es correcte i esta ALIVE enviem HELLO*/
    if(strcmp(registres[i] -> numAleat,recvPDU.numAleat) == 0
      && strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0 && strcmp(registres[i] -> IP, inet_ntoa(udpRecvAdress.sin_addr)) == 0
      && (registres[i] -> estat == STATE_REGIST || registres[i] -> estat == STATE_ALIVE)){

      if(registres[i] -> estat == STATE_REGIST){
        registres[i] -> timing = time(NULL);
        registres[i] -> estat = STATE_ALIVE;

        makeUDPPDU(HELLO, serverInfo, &sendPDU, registres[i] -> numAleat , error);
        sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
        printf("Confirmacio ALIVE  %s\n",registres[i] ->nomEquip);
        if(debug == 1){
          printf("[DEBUG] -> REBUT:   MAC: %s ALEA: %s  DADES: %s\n",recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
          printf("[DEBUG] -> ENVIAT: PAQUET: HELLO MAC: %s ALEA: %s  DADES: %s\n",sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
        }

      }else if (registres[i] -> estat == STATE_ALIVE){
        registres[i] -> timing = time(NULL);
        makeUDPPDU(HELLO, serverInfo, &sendPDU, registres[i] -> numAleat , error);
        sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);

        printf("Confirmacio ALIVE  %s\n",registres[i] ->nomEquip);
        if(debug == 1){
          printf("[DEBUG] -> REBUT: MAC: %s ALEA: %s  DADES: %s\n", recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
          printf("[DEBUG] -> ENVIAT: PAQUET: HELLO MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
        }

      }
      break;

    }

    /*Si l'equip esta desconectat enviem un HELLO_REJ informant de l'error*/
    else if(strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0
    && registres[i] -> estat == STATE_DISCON){
      strcpy(error,"Equip no Registrat");
      strcpy(alea,"00000000");
      strcpy(mac,"000000000000");


      makeErrorPDU(HELLO_REJ, mac, &sendPDU, alea , error);
      sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
      if(debug == 1){
        printf("[DEBUG] -> REBUT: MAC: %s ALEA: %s  DADES: %s\n", recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
        printf("[DEBUG] -> ENVIAT: PAQUET: HELLO MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
      }
      exit(0);
    }

    /*Si el numero aleatori es incorrecte informem*/
    else if(strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0
    && registres[i] -> estat == STATE_REGIST && strcmp(registres[i] -> IP, inet_ntoa(udpRecvAdress.sin_addr)) == 0 && strcmp(registres[i] -> numAleat, recvPDU.numAleat) != 0){
      strcpy(error,"Numero Aleatori Incorrecte");
      strcpy(alea,"00000000");
      strcpy(mac,"000000000000");


      makeErrorPDU(HELLO_REJ, mac, &sendPDU, alea , error);
      sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
      if(debug == 1){
        printf("[DEBUG] -> REBUT: MAC: %s ALEA: %s  DADES: %s\n",recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
        printf("[DEBUG] -> ENVIAT: PAQUET: HELLO_REJ MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
      }
      exit(0);
    }

    /*Si la IP es incorrecta informem*/
    else if(strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0
    && registres[i] -> estat == STATE_REGIST && strcmp(registres[i] -> numAleat, recvPDU.numAleat) == 0
    && strcmp(registres[i] -> IP, inet_ntoa(udpRecvAdress.sin_addr)) != 0){
      strcpy(error,"IP incorrecta");
      strcpy(alea,"00000000");
      strcpy(mac,"000000000000");


      makeErrorPDU(HELLO_REJ, mac, &sendPDU, alea , error);
      sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
      if(debug == 1){
        printf("[DEBUG] -> REBUT:   MAC: %s ALEA: %s  DADES: %s\n", recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
        printf("[DEBUG] -> ENVIAT: PAQUET: HELLO_REJ   MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
      }
      exit(0);
    }

    /*Si la EQUIP es incorrecte informem*/
    else if(strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0 && registres[i] -> estat == STATE_REGIST &&
    strcmp(registres[i] -> numAleat, recvPDU.numAleat) == 0  && strcmp(registres[i] -> IP, inet_ntoa(udpRecvAdress.sin_addr)) == 0){
      strcpy(error,"Nom Equip incorrecte");
      strcpy(alea,"00000000");
      strcpy(mac,"000000000000");


      makeErrorPDU(HELLO_REJ, mac, &sendPDU, alea , error);
      sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
      if(debug == 1){
        printf("[DEBUG] -> REBUT:   MAC: %s ALEA: %s  DADES: %s\n", recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
        printf("[DEBUG] -> ENVIAT: PAQUET: HELLO_REJ   MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
      }
      exit(0);
    }
  }
  /*Si em comprovat tots els equips i no em trobat el que ha enviat l'ALIVE enviem un ALIVE REJ i informem de l'error*/
  if(i == lines){
    strcpy(error,"Equip no autoritzat en el sistema");
    strcpy(alea,"00000000");
    strcpy(mac,"000000000000");


    makeErrorPDU(HELLO_REJ, mac, &sendPDU, alea , error);
    registres[i] -> estat = STATE_DISCON;
    if(debug == 1){
      printf("[DEBUG] -> REBUT:   MAC: %s ALEA: %s  DADES: %s\n", recvPDU.adresaMac,recvPDU.numAleat,recvPDU.Dades);
      printf("[DEBUG] -> ENVIAT: PAQUET: HELLO_REJ   MAC: %s ALEA: %s  DADES: %s\n", sendPDU.adresaMac,sendPDU.numAleat,sendPDU.Dades);
    }
  }
  exit(0);
}

/*PDU en cas de error*/
void makeErrorPDU(unsigned char sign, char mac[], struct PDU_UDP *sendPDU, char random[], char error[]){
  sendPDU -> tipusPacket = sign;
  strcpy(sendPDU -> adresaMac, mac);
  strcpy(sendPDU -> numAleat,random);
  strcpy(sendPDU -> Dades, error);
}
/*Peticions de registre*/
void request(int udpSocket, int lines, struct PDU_UDP recvPDU,  struct sockaddr_in udpRecvAdress, struct SERVINFO serverInfo){
  int i;
  char random[9] = "",error[80] = "";
  struct PDU_UDP sendPDU;
  socklen_t addrlen = sizeof(udpRecvAdress);

  /*Comprovació de existencia del equip dins de'ls equips registrats*/
  for(i = 0; i < lines; i++){
    if(strcmp(registres[i] -> adresaMac,recvPDU.adresaMac) == 0){

      if(registres[i] -> estat == STATE_DISCON && (strcmp("00000000",recvPDU.numAleat) == 0 || strcmp(registres[i] -> numAleat,recvPDU.numAleat) == 0)){

          /*Enviament de numero aleatori depenen de si en te un asignat o no*/
          if(strcmp(registres[i] -> numAleat,"00000000") == 0){
            modifyPCRegisters(i, udpRecvAdress);
          }
          makeUDPPDU(SUBS_ACK, serverInfo, &sendPDU, registres[i] -> numAleat, serverInfo.UDP);
          sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);

          registres[i] -> timing = time(NULL);
          registres[i] -> estat = STATE_REGIST;

          printf("L'equip %s passa a l'estat REGISTRAT\n",registres[i] -> nomEquip);
          break;

          /*En cas de que l'equip estigui conectat enviament de REGISTER REJ*/
      }else if(registres[i] -> estat == STATE_REGIST || registres[i] -> estat == STATE_ALIVE){

        sprintf(error,"%s","Equip conectat");
        makeUDPPDU(SUBS_NACK, serverInfo, &sendPDU, random, error);
        sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
      }
    }
  }
  /*Si despres de comprovar els equips no es troba el que ha enviat la PDU es torna un error*/
  if(i == lines){

    strcpy(error, "Equip no autoritzat en el sistema\0");
    makeUDPPDU(SUBS_REJ, serverInfo, &sendPDU, random, error);
    sendto(udpSocket, &sendPDU, BUFSIZEUDP,0, (struct sockaddr *)&udpRecvAdress, addrlen);
  }
}

/*Modificar els valors de IP i numero aleatori del equip registrat*/
void modifyPCRegisters(int i, struct sockaddr_in udpRecvAdress){
  char random[7];

  sprintf(random,"%d",randomGenerator());
  registres[i] -> estat = 1;
  sprintf(registres[i] -> numAleat,"%8s", random);
  sprintf(registres[i] -> IP,"%9s", inet_ntoa(udpRecvAdress.sin_addr));
}

/*generador del nombre aleatori*/
int randomGenerator(){
  int random;
  srand(time(NULL));
  random = rand()%90000000+10000000;

  return random;
}
