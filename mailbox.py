#*********************************************************************
#
#   MODULE NAME:
#       mailbox.py - mailboxAPI Interfacing Class
#
#   DESCRIPTION:
#       Class to provide functionaility for interacting with the Raspberry
#		pi pico through the mailboxAPI
#
#   Copyright 2025 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#--------------------------------------------------------------------- 
import time
from msgAPI import messageAPI
#---------------------------------------------------------------------
#                              VARIABLES
#--------------------------------------------------------------------- 
global_mailbox = [
# data, type,   flag,  dir,  src,           dest
[ 0,   'ASYNC', False, 'RX', 'RPI_MODULE',  'PICO_MODULE' ],
[ 0.0, '1',     False, 'TX', 'PICO_MODULE', 'RPI_MODULE'  ] ]

#---------------------------------------------------------------------
#                              CONSTANTS
#--------------------------------------------------------------------- 
ACK_ID        = 0xFF
MSG_UPDATE_ID = 0xFE

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------

class Mailbox():
    def __init__(self, msg_conn, gbl_mailbox, manage_lst = None ):
        self.msg_conn = msg_conn

        # By default we only manage ourself, however to support testing the option to
        # fake other units was added here
        # self.manage_list = [ msg_conn.currentModule ] if manage_lst is None else manage_lst
        if manage_lst != None:
            # we need to make changes to msgAPI to provide destination data before we can implement here
            raise( NotImplementedError )

        self.mailbox_map   = gbl_mailbox
        self.round_counter = 0 # round counter always starts at 0 
        self.ack_list     = []
        self.current_round = 0

        self.tx_queue = []

        #
    def mailbox_runtime( self ):
        self.rx_runtime()
        self.tx_runtime()


    def rx_runtime( self ):
        raise( NotImplementedError)
        # self.tx_queue.append( ['ack', idx])


    def tx_runtime( self ):
        if self.round_counter == self.msg_conn.currentModule:

            #determine which entries need handling
            for idx, [data, rate, flag, dir, src, dest] in enumerate(self.mailbox_map):
                if src ==  self.msg_conn.currentModule:
                    if ( rate == 'ASYNC' and flag == True ) or ( rate != 'ASYNC' and (int(rate)%self.round_counter == 0) ):
                        self.tx_queue.append( ['data', idx] )


            self.tx_queue.append( [ 'round', 0 ] ) 

            self.__msg_interface_pack_and_send()

            #update round counter
            self.round_counter = (self.round_counter + 1 )% 100 

    def __msg_interface_pack_and_send( self ):
        for type, data in self.tx_queue:
            print()

        #empty tx queue
        self.tx_queue = []



#---------------------------------------------------------------------
#                               MAIN
#---------------------------------------------------------------------
def main():
    # pico = pi_pico()
    msg_conn = messageAPI(  bus = 0, 
                            chip_select = 0, 
                            currentModule = 0x00, 
                            listOfModules=[0x00,0x01,0x02] )
    mailbox = Mailbox_manager( msg_conn )

    while( True ):

#---------------------------------------------------------------------
#                              RUN
#---------------------------------------------------------------------
if __name__ == "__main__":
    main()