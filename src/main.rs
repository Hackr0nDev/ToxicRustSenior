// Online C compiler to run C program online
#include <stdio.h>
#include<stdlib.h>

typedef struct node{
    int value; 
    struct node *next;
}Node;

typedef struct stack{
    Node *front;
}Stack;

int init(Stack *q){
    if(q == NULL){return -1;}
    q -> front = NULL;
    return 0;
}




int push(Stack *q, int val){
    if(q == NULL) return -1;
    Node *tmp = malloc(sizeof(Node));
    if(tmp == NULL){return -2;}
    tmp -> value = val;
    tmp -> next = q -> front;
    q -> front = tmp;
    return 0;
}

int pop(Stack *q){
    if(q == NULL) return -1;
    if(q -> front == NULL) return -2;
    Node *tmp = q -> front;
    if(tmp == NULL) return -3;
    int val = tmp -> value;
    q -> front = q -> front -> next;
    free(tmp);
    return val;
}



int clear(Stack *q){
    if(q == NULL) return -1;
    if(q -> front == NULL) return 1;
    while(q -> front != NULL){
        Node *tmp = q -> front;
        q -> front = q -> front -> next;
        free(tmp);
    }
    return 0;
}

int printStack(Stack *q){
    if(q == NULL){return -1;}
    if(q -> front == NULL){printf("aaaa");return -2;}
    Node *tmp = q -> front;
    while(tmp != NULL){
        printf("%d ", tmp -> value);
        tmp = tmp -> next;
    }
    printf("\n");
    return 0;
}



int main() {
    Stack *q = malloc(sizeof(Stack));
    init(q);
    
    push(q, 10);push(q, 11);push(q, 13);

    printStack(q);
    pop(q);
    printStack(q);
    clear(q);
    printStack(q);
    
    return 0;
}
