# Yuanming Song (ysong33)

# references:
# https://beej.us/guide/bgnet/html/
# https://realpython.com/python-sockets/#tcp-sockets
# https://pythonprogramming.net/sockets-tutorial-python-3/

# 2.7.2 Socket Programming with TCP
""" from socket import *
HOST = 'servername'
POST = 12000
client_socket = socket(AF_INET, SOCK_STREAM)
client_socket.connect((HOST,POST))
sentence = input('Input lowercase sentence:')
client_socket.send(sentence.encode())
DATA = client_socket.recv(1024)
print('From Server: ', DATA.decode())
client_socket.close() """

import sys
import socket

# messages for client input
INPUT_MSG = [
    'The bidding has started!\n', 'Please submit auction request:\n',
    'Invalid bid. Please submit a positive integer!\n',
    'some wrong input \nServer: Invalid auction request!\nPlease submit auction request:\n'
]

# message for close connection
CLOSE_CONNECTION_MSG = [
    'Bidding on-going!\n', 'Server is busy. Try to connect again later.\n'
]

# check HOST and POST
if len(sys.argv) < 3:
    print('Please enter the server HOST and POST to connect.')
    sys.exit()

HOST = sys.argv[1]

try:
    POST = int(sys.argv[2])

except ValueError:
    print('Invalid POST value.')
    sys.exit()

# creates the client’s socket
# initiates the TCP connection between the client and server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, POST))

DATA = ''

# loop for input check
while True:
    DATA = client_socket.recv(1024)

    if not DATA:
        # close connection if not DATA
        break

    if DATA.endswith(b'\n'):
        print(DATA.decode('utf-8'))

        if any(DATA.endswith(msg.encode()) for msg in CLOSE_CONNECTION_MSG):
            break

        if any(DATA.endswith(msg.encode()) for msg in INPUT_MSG):
            user_input = input()

            # send the sentence through the client’s socket and into the TCP connection
            client_socket.send((user_input + '\n').encode())

        DATA = ''

# close the TCP connection between the client and the server
client_socket.close()
