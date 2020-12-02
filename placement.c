#include<stdio.h>
#include<stdlib.h>
#include<string.h>
int main(int argc,char *argv[]) {
        char command[50]={"python3 /home/eda20303/project/code/main.py -d "};
        strcat(command,argv[1]);
        printf("%s",command);
        system(command);
}
