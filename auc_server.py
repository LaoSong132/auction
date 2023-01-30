# Yuanming Song (ysong33)

# references:
# https://beej.us/guide/bgnet/html/
# https://realpython.com/python-sockets/#tcp-sockets
# https://pythonprogramming.net/sockets-tutorial-python-3/

# 2.7.2 Socket Programming with TCP
""" from socket import *
serverPort = 12000
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind(('',serverPort))
serverSocket.listen(1)
print('The server is ready to receive')
while True:
 connection_socket, addr = serverSocket.accept()
 sentence = connection_socket.recv(1024).decode()
 capitalizedSentence = sentence.upper()
 connection_socket.send(capitalizedSentence.encode())
 connection_socket.close() """

import sys
import socket
import threading
from enum import IntEnum

HOST = ''

# check if user enter the PORT number
if len(sys.argv) < 2:
    print('Please enter the PORT for the auction server.')
    sys.exit()

try:
    PORT = int(sys.argv[1])

except ValueError:
    print('Invalid PORT number.')
    sys.exit()

# implementing primitive lock objects
lock = threading.Lock()

# auction states
AUCTION_STATE = None  # current auction state
SELLER_STATE = None  # current seller status


class Auction:
    """ class for auction """

    def __init__(self, type_of_auction, min_price, num_of_bids, item_name):
        self.type_of_auction = type_of_auction
        self.min_price = min_price
        self.num_of_bids = num_of_bids
        self.item_name = item_name
        self.bids = []

    def add_bid(self, bidder_id, bid_amount):
        """ add a bid """
        self.bids.append((bidder_id, bid_amount))

    def get_all_bids(self):
        """ get all bids """
        return len(self.bids) == self.num_of_bids

    def find_winning_bid(self):
        """ check which client will win the auction """
        sorted_bids = sorted(self.bids, key=lambda x: x[1], reverse=True)
        winning_bid = None

        if self.type_of_auction == 2:
            winning_bid = (sorted_bids[0][0], sorted_bids[1][1])
        winning_bid = sorted_bids[0]

        # make sure bid higher than min price
        if winning_bid[1] >= self.min_price:
            return winning_bid
        return (None, None)


def get_current_auction():
    """ get current auction """
    with lock:
        return AUCTION_STATE


def set_current_auction(auction):
    """ set current auction """
    with lock:
        global AUCTION_STATE
        AUCTION_STATE = auction


class ServerStatus(IntEnum):
    """ server states """
    WAITING_FOR_SELLER = 0
    WAITING_FOR_BUYER = 1


SERVER_STATUS = ServerStatus.WAITING_FOR_SELLER


def get_server_status():
    """ get server status """
    with lock:
        return SERVER_STATUS


def set_server_status(status):
    """ set server status """
    print('Setting server status to ' + status.name)
    with lock:
        global SERVER_STATUS
        SERVER_STATUS = status
        print('Server status set to ' + status.name)


class Client(threading.Thread):
    """ client class """

    def __init__(self, connection_socket):
        super(Client, self).__init__()
        self.connection_socket = connection_socket
        self.data = ''

    def send_msg(self, msg):
        """ send message """
        self.connection_socket.send(msg.encode())

    def run(self):
        print('New client thread spawned')

        # connection message to server
        self.send_msg('Connected to the Auctioneer server.\n')

    def close(self):
        """ close connection """
        self.connection_socket.close()


class Seller(Client):
    """ seller class """

    def __init__(self, connection_socket):
        super(Seller, self).__init__(connection_socket)
        self.is_auctioning = True

    def run(self):
        super().run()

        # role information for client
        self.send_msg('Your role is: [Seller]\n')
        self.send_msg('Please submit auction request:\n')

        while self.is_auctioning:
            try:
                self.data = self.data + \
                    self.connection_socket.recv(1024).decode('utf-8')

                if self.data.endswith('\n'):
                    # check for server status
                    if SERVER_STATUS == ServerStatus.WAITING_FOR_SELLER:
                        auction_request = self.data.strip().split(' ')

                        # auction request input handling
                        try:
                            if len(auction_request) < 4:
                                raise ValueError('Missing auction parameters')

                            type_of_auction = int(auction_request[0])
                            if type_of_auction not in {1, 2}:
                                raise ValueError(
                                    'Auction type must be either 1 for first-price or 2 for second-price'
                                )

                            auction_min_price = int(auction_request[1])
                            if auction_min_price < 0:
                                raise ValueError(
                                    'Invalid bid. The min price must be a positive integer'
                                )

                            auction_num_of_bids = int(auction_request[2])
                            if auction_num_of_bids < 0 or auction_num_of_bids > 9:
                                raise ValueError(
                                    'Number of bids must be a less than 10 positive integer'
                                )

                            auction_item_name = auction_request[3]
                            if len(auction_item_name) > 255:
                                raise ValueError(
                                    'Item name must less than 255 characters')

                            # if the auction request valid, start the auction
                            set_current_auction(
                                Auction(type_of_auction=type_of_auction,
                                        min_price=auction_min_price,
                                        num_of_bids=auction_num_of_bids,
                                        item_name=auction_item_name.strip()))
                            self.send_msg(
                                'Auction request received. Now waiting for Buyer.'
                            )

                            # set the server status to waiting for buyer
                            set_server_status(ServerStatus.WAITING_FOR_BUYER)

                        except ValueError:
                            self.send_msg(
                                'some wrong input \nServer: invalid auction request!\nPlease submit auction request:\n'
                            )
                    else:
                        self.send_msg(
                            'The Auctioneer is still waiting for other Buyer to connect...\n'
                        )

                    self.data = ''
            except OSError:
                break


class Buyer(Client):
    """ buyer class """

    def __init__(self, connection_socket, bidder_id):
        super(Buyer, self).__init__(connection_socket)
        self.bidder_id = bidder_id
        self.bid = None

    def run(self):
        super().run()

        # assign the client a role
        self.send_msg('Your role is: [Buyer]\n')

        while True:
            # check if the buyer submit a bid
            if not self.bid:
                self.data = self.data + \
                    self.connection_socket.recv(1024).decode('utf-8')

                if self.data.endswith('\n'):
                    try:
                        # set the bid for the auction
                        self.bid = int(self.data.strip())
                        get_current_auction().add_bid(self.bidder_id, self.bid)

                        print(
                            f"Bid recieved from bidder {self.bidder_id}: {self.bid}"
                        )

                        self.send_msg('Server: Bid received. Please wait...\n')

                    except ValueError:
                        self.send_msg(
                            'Invalid bid. Please submit a positive integer.\n')

                    self.data = ''


class BiddingThread(threading.Thread):
    """ bidding thread class """

    def __init__(self, buyers):
        super(BiddingThread, self).__init__()
        self.buyers = buyers

    def run(self):
        print('Bidding thread spawned')

        global SELLER_STATE

        # send bidding has started message to seller
        SELLER_STATE.send_msg('The bidding has started!\n')

        # send bidding has started message to buyers
        for buyer in self.buyers:
            buyer.send_msg('The bidding has started!\n')

        while True:
            auction = get_current_auction()

            if auction.get_all_bids():
                winning_bidder_id, winning_bid = auction.find_winning_bid()
                losing_buyers = [
                    buyer for buyer in self.buyers
                    if buyer.bidder_id != winning_bidder_id
                ]

                # send message to losing buyers
                for buyer in losing_buyers:
                    buyer.send_msg(
                        'Unfortunately you did not win in the last round.\n')
                    buyer.close()

                # if there is a winner, send the message
                if winning_bidder_id is None:
                    SELLER_STATE.send_msg(
                        'Unfortunately, the item was not sold in the auction.\n'
                    )
                else:
                    SELLER_STATE.send_msg(
                        f"The item {auction.item_name} sold for ${winning_bid}.\n"
                    )

                    winning_buyer = self.buyers[winning_bidder_id]

                    winning_buyer.send_msg(
                        f"You won this item {auction.item_name}! Your payment due is ${winning_bid}.\n"
                    )
                    winning_buyer.send_msg(
                        "Disconnecting from the Auctioneer server. Auction is over!\n"
                    )
                    winning_buyer.close()

                # Close seller connection
                SELLER_STATE.is_auctioning = False
                SELLER_STATE.close()
                SELLER_STATE = None

                # reset auction and exit thread
                set_current_auction(None)
                set_server_status(ServerStatus.WAITING_FOR_SELLER)
                break


class ConnThread(threading.Thread):
    """ connection thread """

    def __init__(self, HOST, PORT):
        super(ConnThread, self).__init__()

        try:
            self.serverSocket = socket.socket(socket.AF_INET,
                                              socket.SOCK_STREAM)
            self.serverSocket.bind((HOST, PORT))
            self.serverSocket.listen(10)
            print('Auctioneer is ready for hosting auctions.')

        except socket.error:
            print('Failed to create socket')
            sys.exit()

        self.buyers = []

    def run(self):
        global SELLER_STATE

        while True:
            try:
                connection_socket, addr = self.serverSocket.accept()
                client = None

                # return current auction
                auction = get_current_auction()

                if SELLER_STATE:
                    # if there is a seller thread
                    if get_server_status() == ServerStatus.WAITING_FOR_SELLER:

                        # wait until the auction end
                        connection_socket.send(
                            'Server is busy. Try to connect again later.\n')
                        connection_socket.close()
                    else:
                        # for new buyers enter the auction
                        client = Buyer(connection_socket,
                                       bidder_id=len(self.buyers))
                        self.buyers.append(client)
                        client.start()

                        if len(self.buyers) == auction.num_of_bids:
                            # send buyers to bidding thread
                            bidding = BiddingThread(self.buyers)
                            bidding.start()
                            # reset buyer
                            self.buyers = []
                        if len(self.buyers) > auction.num_of_bids:
                            # bidding on-going
                            client.send_msg('Bidding on-going.\n')
                            client.close()
                        else:
                            # waiting for buyers
                            client.send_msg(
                                'The Auctioneer is still waiting for other Buyer to connect...\n'
                            )
                else:
                    # the first client would be the seller
                    client = Seller(connection_socket)
                    SELLER_STATE = client
                    client.start()
            except (KeyboardInterrupt, socket.error):
                sys.exit()


def main():
    """ main """
    set_connection = ConnThread(HOST, PORT)
    set_connection.start()


if __name__ == '__main__':
    main()
