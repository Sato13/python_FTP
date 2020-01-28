
import os
import socket
import json
import glob
import time

import bz2  # dependency for compression

# from Crypto.PublicKey import RSA  # dependency for encryption
# from Crypto import Random  # dependency for encryption

from validate_email import validate_email  # dependency for check_email function

# globals for server connection
#HOST = socket.gethostbyname(socket.gethostname())
HOST = '172.20.10.5'
PORT = 12000
s_server = socket.socket()  # create socket
s_server.bind((HOST, PORT))  # bind to localhost and port
s_server.listen(1)  # allow max of 1 connections to be queued
conn, addr = s_server.accept()
print('Waiting for connection...')

# globals for ASCII/BINARY transfer
ASCII = 'ASCII'
BINARY = 'BIANRY'
TRANS_MODE = ASCII  # transfer mode


# Below are the methods for client commands


def pwd():
    """
    pwd - print working directory (same as 'dir' command in Windows)
    allows client to print the current directory
    """
    result = os.getcwd()  # get current directory
    return result.encode()  # encode for client


def dir(cmd):
    """
    dir - lists contents of remote directory
    allows client to list files in a remote directory
    """
    conn.send('Listing'.encode())
    files = []

    time.sleep(.1)
    for stuff in os.listdir(cmd):
        files.append(stuff + '\n')
    for items in files:
        conn.send(items.encode())
    time.sleep(.1)
    conn.send('done'.encode())  # lets client know listing is finished


def cd(cmd):
    """
    cd - change directory
    allows client to change to a directory of their choice
    """
    if os.path.isdir(cmd):
        os.chdir(cmd)  # change directory
        conn.send('DIRECTORY CHANGED'.encode())
    else:
        conn.send('DIRECTORY DOES NOT EXIST'.encode())


def ls(cmd):
    """
    ls - list directory
    lists all files inside current directory
    supports WILDCARDS *
    """
    conn.send('Listing'.encode())
    print('debug')
    files = []

    time.sleep(.1)
    if len(cmd) == 0:  # if no specified file is given, list all files in directory
        for stuff in os.listdir(os.getcwd()):
            files.append(stuff + '\n')
        for items in files:
            conn.send(items.encode())
        time.sleep(.1)
        conn.send('done'.encode())  # lets client know listing is finished
        print('debug2')

    elif len(cmd) > 0:  # if user specifies something after 'ls'
        for specific in glob.glob(cmd):
            files.append(specific + '\n')  # only add specific files to array

        if len(files) < 1:
            conn.send('No files matching that pattern!'.encode())
            conn.send('done'.encode())  # lets client know listing is finished
        else:
            for items in files:
                conn.sendall(items.encode())
            time.sleep(.1)
            conn.send('done'.encode())  # lets client know listing is finished


def get(cmd):
    """
    get - download file
    allows client to download file so long as it exists
    """
    global TRANS_MODE  # so get() can see global variable
    global COMPRESS_MODE

    if os.path.isfile(cmd):  # check if file exists first
        f = open(cmd, 'rb')  # open in read only, binary
        conn.send('File exists'.encode())  # send confirmation msg
        choice = conn.recv(1024).decode()  # get client decision
        if choice == 'yes':  # if yes, send the file

            if COMPRESS_MODE:  # compress file and send if COMPRESSION enabled
                compressor_new = bz2.BZ2Compressor()  # prevent flush() error. refreshes compressor for multiple files
                compressed_data = b''  # new compressed data we will send
                while True:
                    f_data = f.read()
                    if f_data == b'':  # stop when reach EOF
                        break
                    compressed_data += compressor_new.compress(f_data)
                compressed_data += compressor_new.flush()
                conn.sendall(compressed_data)
                f.close()

            else:
                while True:
                    f_data = f.read()  # read contents and store
                    if f_data == b'':  # stop when reached EOF
                        break
                    time.sleep(.1)
                    conn.sendall(f_data)  # send the file
                    #conn.send('done'.encode()) # send confirmation
            f.close()  # close the file

        elif choice == 'no':
            f.close()  # close the file. server is sad that you didn't want the file
    else:
        conn.send("File does not exist!".encode())


def mget():
    """
    mget - download multiple files
    """
    global TRANS_MODE, COMPRESS_MODE
    conn.send('mget'.encode())  # lets client know to start
    choice = conn.recv(1024).decode()  # yes or no

    if choice == 'yes':
        obj_recv = json.loads(conn.recv(1024).decode())  # receive file names, deserialize the list object
        counter = 0  # keep up with which file we're on

        while counter < len(obj_recv):
            if os.path.isfile(obj_recv[counter]):  # check if file exists
                f = open(obj_recv[counter], 'rb')
                if COMPRESS_MODE:  # if compression is enabled, compress it
                    compressor_new = bz2.BZ2Compressor()  # prevent flush() error. refreshes compressor for multiple files
                    compressed_data = b''  # new compressed data we will send
                    while True:
                        f_data = f.read()
                        if f_data == b'':  # stop when reach EOF
                            break
                        compressed_data += compressor_new.compress(f_data)  # append
                    compressed_data += compressor_new.flush()
                    conn.sendall(compressed_data)  # send compressed data
                    f.close()

                else:
                    while True:
                        f_data = f.read()
                        if f_data == b'':
                            break
                        time.sleep(.1)
                        conn.sendall(f_data)
                    f.close()
                counter += 1  # increment to next file
                conn.recv(1024).decode()  # wait until client sends the okay to keep going
            else:
                print('Not a file')
                continue
    else:
        print('choice was no')


def put(cmd):
    """
    put - uploads file to server
    """
    global COMPRESS_MODE

    conn.send('put'.encode())  # confirm for client
    time.sleep(.1)
    conn.send(cmd.encode())  # send file name back to client
    f = open('server_' + cmd, 'wb')

    choice = conn.recv(1024).decode()

    if choice == 'y':
        if COMPRESS_MODE:  # if compression enabled
            decompress_new = bz2.BZ2Decompressor()  # refresh decompressor for multiple files

            while True:
                f_data = conn.recv(1024)
                f.write(decompress_new.decompress(f_data))  # decompress
                print(str(len(f_data)) + ' bytes')
                if len(f_data) < 1024:
                    break
            f.close()
            conn.send('UPLOAD COMPLETE'.encode())  # confirm for client

        else:
            while True:
                f_data = conn.recv(1024)
                print('debug')
                f.write(f_data)
                print(str(len(f_data)) + ' bytes')
                if len(f_data) < 1024:
                    break
            f.close()
            time.sleep(.1)
            conn.send('UPLOAD COMPLETE'.encode())  # confirm for client
    if choice == 'n':
        f.close()
        pass


def mput():
    """
    mput - uploads multiple files to server
    """
    conn.send('mput'.encode())  # lets client know to start
    files_recv = json.loads(conn.recv(1024).decode())  # grab file names

    counter = 0  # keep up with which files we're on

    while counter < len(files_recv):
        f = open('server_' + files_recv[counter], 'wb')

        decompress_new = bz2.BZ2Decompressor()  # refresh decompressor for multiple files
        if COMPRESS_MODE:  # if compression enabled
            while True:
                f_data = conn.recv(1024)
                if len(f_data) < 1024:
                    break
                print(str(len(f_data)) + ' compressed bytes')
                f.write(decompress_new.decompress(f_data))  # decompress data
            f.close()
            print('220 UPLOAD COMPLETE')
            counter += 1  # increment to next file
            conn.send('okay'.encode())  # let client know its okay to send more
        else:
            while True:
                f_data = conn.recv(1024)
                print('debug')
                f.write(f_data)
                print(str(len(f_data)) + ' bytes')
                if len(f_data) < 1024:
                    break
            f.close()
            counter += 1  # increment to next file
            conn.send('okay'.encode())  # let client know its okay to send more

            # conn.sendall('220 UPLOAD COMPLETE'.encode())


def check_email(email):
    """
    checks if email if valid
    """
    valid = validate_email(email)
    if valid:
        return True

    return False


def menu():
    conn.send("help -> display this menu\n"
              "cd   -> change directory\n"
              "pwd  -> print working directory\n"
              "dir [path] -> lists contents of remote directory\n"
              "ls   -> lists all the files in the directory\n"
              "get [file] -> grabs file from server and downloads it to the local machine\n"
              "put [file] -> grabs file from local machine and uploads it to the server\n"
              "mget -> grabs multiple files from the server and downloads them to the local machine\n"
              "mput -> grabs multiple files from the local machine and uploads them to the server\n"
              "ASCII -> enables ASCII transfer mode\n"
              "BINARY -> enables BINARY transfer mode\n"
              "compress -> enables file compression\n"
              "normal -> disables encryption and compression\n"
              "quit -> closes connection\n"
              "\nPlease enter a command: ".encode())


def anon_auth(user, pw):
    """
    authorize an anonymous user
    username must be 'anonymous'
    and pass must be in form of valid e-mail
    """
    if user == 'anonymous' and check_email(pw):
        conn.send("ftp> Client has connected to the server.\n\n"
                  "help -> display this menu\n"
                  "cd   -> change directory\n"
                  "pwd  -> print working directory\n"
                  "dir [path] -> lists contents of remote directory\n"
                  "ls   -> lists all the files in the directory\n"
                  "get [file] -> grabs file from server and downloads it to the local machine\n"
                  "put [file] -> grabs file from local machine and uploads it to the server\n"
                  "mget -> grabs multiple files from the server and downloads them to the local machine\n"
                  "mput -> grabs multiple files from the local machine and uploads them to the server\n"
                  "ASCII -> enables ASCII transfer mode\n"
                  "BINARY -> enables BINARY transfer mode\n"
                  "compress -> enables file compression\n"
                  "normal -> disables encryption and compression\n"
                  "quit -> closes connection\n"
                  "\nPlease enter a command: ".encode())
    else:
        conn.send("User or Password incorrect. Bye.".encode())
        conn.close()  # close connection


def run():
    global TRANS_MODE  # so run() can see global variable
    global ENCRYPT_MODE
    global COMPRESS_MODE

    print('Got connection from: ' + str(addr))

    conn.send("enter username: ".encode())  # ask for username
    username = conn.recv(1024).decode()  # receive
    conn.send("enter pass: ".encode())  # ask for pass
    pw = conn.recv(1024).decode()  # receive
    anon_auth(username, pw)  # check credentials

    while True:
        cmd = conn.recv(1024).decode()  # variable to handle commands sent by client

        if cmd == 'pwd':
            conn.send(pwd())
            continue
        if cmd[0:3] == 'dir':
            dir(cmd[4:])  # get rest of the cmd after 'dir'
            continue
        elif cmd[0:2] == 'cd':
            cd(cmd[3:])  # get the rest of the cmd after 'cd'
            continue
        elif cmd[0:3] == 'get':
            get(cmd[4:])  # get the rest of cmd after 'get'
            conn.send('220 DOWNLOAD COMPLETE'.encode())
            continue
        elif cmd == 'mget':
            mget()
            continue
        elif cmd[0:3] == 'put':
            put(cmd[4:])  # get the rest of cmd after 'put'
            continue
        elif cmd == 'mput':
            mput()
            continue
        elif cmd[0:2] == 'ls':
            ls(cmd[3:])  # get the rest of cmd after 'ls'
            continue
        elif cmd == 'ASCII':
            TRANS_MODE = ASCII
            conn.send('220 ASCII mode enabled'.encode())  # confirmation for client
            continue
        elif cmd == 'BINARY':
            TRANS_MODE = BINARY
            conn.send('220 BINARY mode enabled'.encode())  # confirmation for client
            continue
        elif cmd == 'compress':
            COMPRESS_MODE = not COMPRESS_MODE  # toggle compression
            if COMPRESS_MODE:
                time.sleep(.1)
                conn.send('220 Compression enabled'.encode())
            else:
                time.sleep(.1)
                conn.send('220 Compression disabled'.encode())
            continue
        elif cmd == 'normal':
            ENCRYPT_MODE = False
            COMPRESS_MODE = False
            time.sleep(.1)
            conn.send('220 encryption and compress disabled'.encode())
            continue
        elif cmd == 'help':  # display help menu
            menu()
            continue
        elif cmd == 'quit':
            conn.send('220 Goodbye!'.encode())
            conn.close()  # close the connection
            break
        else:
            conn.send("502 Command not implemented".encode())

        if not cmd:
            conn.close()
            break


def main():
    run()  # start FTP


if __name__ == '__main__':
    main()
