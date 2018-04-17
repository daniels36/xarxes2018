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

#define LIST "list"
#define QUIT "quit"
#define MAP_ANONYMOUS 0x20
#define NUMCOMPUTERS 100

struct PCREG *registres[NUMCOMPUTERS];
struct PCREG{
  char nomEquip[7];
  char adresaMac[13];
  char IP[9];
  int estat;
  char numAleat[7];
  long timing;
};

struct SERVINFO{
  char nomServ[9];
  char MAC[13];
  char UDP[5];
  char TCP[5];
};

struct SERVINFO serverInfo;
int debug;
int pidWork, pidAlives, pidMsg;
char servFile[30] = "../cfg/server.cfg\0";
char autorized[30] = "../dat/controlers.dat\0";

void readServInfo(struct SERVINFO *serverInfo);
int readPermitedComputers();
int createUDPSocket();
int createTCPSocket();
void handler(int sig);


int main(int argc, char *argv[]){
  int udpSocket;
  int lines = 0, i;
  char input[5];
  char estat[12];
  printf("IN0\n");
  /*Reserva de espai de memória compartida per a la taula de clients*/
  for(i=0;i<NUMCOMPUTERS;i++){
 	  registres[i] = (struct PCREG *)mmap(0, sizeof(*registres[NUMCOMPUTERS]), PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
  }
  printf("IN1\n");
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

  printf("IN2\n");
  /*Lectura del fitxer d'informació del servidor*/
  readServInfo(&serverInfo);
  /*Lectura del fitxer de equips permesos*/
  printf("IN3\n");
  lines = readPermitedComputers();
  printf("IN4\n");
  pidWork = fork();
  if(pidWork == 0){
    if(debug == 1){
      printf("[DEBUG] -> Preparat procés per a rebre peticions TCP/UDP\n");
    }
    udpSocket = createUDPSocket();

    printf("[DEBUG] -> Preparat per a rebre regitres:\n");
    /*work(udpSocket,serverInfo,lines);
    */
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
            sprintf(estat,"%s","ALIVE");
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
  char ignore[10];
  f = fopen(servFile, "r");
  if(f == NULL){
    printf("El fitxer no existeix");
    exit(0);
  }else{
    /*Llegir la informació del servidor*/
    while(!feof(f)){
      fscanf(f, "%s %8s",ignore, serverInfo -> nomServ);
      fscanf(f, "%s %12s",ignore, serverInfo -> MAC);
      fscanf(f, "%s %5s",ignore, serverInfo -> UDP);
      fscanf(f, "%s %5s",ignore, serverInfo -> TCP);
    }

    fclose(f);
  }
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
  udpSockAdress.sin_port = htons(2016);

  /*Assignació de socket a adreça*/
  if(bind(udpSocket, (struct sockaddr *)&udpSockAdress, sizeof(udpSockAdress)) < 0){
    perror("bind failed");
    return 0;
  }
  return udpSocket;
}

/*Creacio conexió TCP*/
int createTCPSocket(){
  int tcpSocket, portnum;
  struct sockaddr_in serv_addr;

  /*Creació del socket de protocol*/
  tcpSocket = socket(AF_INET, SOCK_STREAM, 0);

  bzero((char *) &serv_addr, sizeof(serv_addr));
  portnum = 6102 ;

  /*Adreça de binding (escolta) -> totes les disponibles */
   memset(&serv_addr,0,sizeof (struct sockaddr_in));
   serv_addr.sin_family = AF_INET;
   serv_addr.sin_addr.s_addr = INADDR_ANY;
   serv_addr.sin_port = htons(portnum);

   /*Assignació del socket a la adreça*/
   if (bind(tcpSocket, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0) {
      perror("ERROR on binding");
      exit(1);
   }

   return tcpSocket;
}

/*Control de senyal*/
void handler(int sig){
  kill(pidAlives,SIGINT);
  kill(pidMsg,SIGINT);
  exit(0);
}
