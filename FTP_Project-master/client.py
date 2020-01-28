
import socket
import os
import json
import glob
import time

import bz2

# from Crypto.PublicKey import RSA

# Connecting client to server
#host = socket.gethostname()
host = '10.20.150.237'
port = 1337
s = socket.socket()
s.connect((host, port))


def pwd():
    result = os.getcwd()  # get current directory
    return result  # encode for client


def mget():
    global COMPRESS_MODE
    WILDCARD = False
    file_amt = 0

    msg = input("Download multiple files to the following location? [y/n] \n" + os.getcwd() + "\n")
    if msg == 'y' or msg == 'Y':
        s.send('yes'.encode())  # send confirm
        files = input('Enter files to download: ').split()  # take file names

        # wildcard support
        if '*' in files[0]:
            WILDCARD = True
            joined_files = ''.join(files)  # glob cannot handle lists, re-join
            wildcard_files = glob.glob(joined_files)  # handle wildcards
            files_obj = json.dumps(wildcard_files)  # serialize the list
        else:
            regular_files = list(map(str, files))  # no wildcards
            files_obj = json.dumps(regular_files)  # serialize the list

        time.sleep(.1)
        data = s.send(files_obj.encode())  # send the serialized data

        counter = 0  # keep up with what file we're on

        if WILDCARD:
            file_amt = len(wildcard_files)
        else:
            file_amt = len(files)

        while counter < file_amt:
            if WILDCARD:  # if wildcards used
                f = open('client_' + wildcard_files[counter], 'wb')
            else:
                f = open('client_' + files[counter], 'wb')  # open file one at a time

            if COMPRESS_MODE:  # if compression enabled
                decompressor_new = bz2.BZ2Decompressor()  # refreshes decompressor for multiple files
                while True:
                    f_data = s.recv(1024)
                    print(str(len(f_data)) + ' compressed bytes')
                    f.write(decompressor_new.decompress(f_data))  # decompress data
                    if len(f_data) < 1024:
                        break
                f.close()
                print('220 DOWNLOAD COMPLETE')
                counter += 1
                s.send('okay'.encode())  # lets server know to send another file

            else:
                while True:
                    f_data = s.recv(1024)
                    f.write(f_data)
                    print(str(len(f_data)) + ' bytes')
                    if len(f_data) < 1024:
                        break
                f.close()
                print('220 DOWNLOAD COMPLETE')
                counter += 1
                s.send('okay'.encode())  # lets server know to send another file

    elif msg == 'n' or msg == 'N':
        s.send('no'.encode())
        print('210 ABORTED')


def get():
    global ENCRYPT_MODE, private_key
    global COMPRESS_MODE

    msg = input("Download file to following location? [y/n] \n" + os.getcwd() + "\n")
    if msg == 'y' or msg == 'Y':
        filename = input("Filename to save as: ")
        s.send('yes'.encode())  # send confirm to server
        f = open('client_' + filename, 'wb')  # open file

        if COMPRESS_MODE:  # if compression enabled, decompress
            decompressor_new = bz2.BZ2Decompressor()  # refreshes decompressor for multiple files
            while True:
                f_data = s.recv(1024)
                print(str(len(f_data)) + ' compressed bytes')
                f.write(decompressor_new.decompress(f_data))  # decompress
                if len(f_data) < 1024:
                    break
            f.close()
            print('220 DOWNLOAD COMPLETE!')

        else:
            while True:
                f_data = s.recv(1024)
                f.write(f_data)  # write bytes
                print(str(len(f_data)) + ' bytes')  # without print statement, get doesn't work???
                if len(f_data) < 1024:
                    break
            f.close()  # close file
            print('220 DOWNLOAD COMPLETE!')
    else:
        print('210 DOWNLOAD ABORTED')
        s.send('no'.encode())


def mput():
    msg = input("Upload files to the following location? [y/n] \n" + str(pwd()) + "\n")
    if msg == 'y' or msg == 'Y':
        files = list(map(str, input('Enter files to upload: ').split()))
        files_obj = json.dumps(files)
        data = s.send(files_obj.encode())  # send file names

        counter = 0  # keep up with which file we're on

        while counter < len(files):
            f = open(files[counter], 'rb')

            if COMPRESS_MODE:  # if compressed enabled
                compressor_new = bz2.BZ2Compressor()  # refresh compressor for multiple files
                compressed_data = b''  # new compressed data we'll send
                while True:
                    f_data = f.read()
                    if f_data == b'':  # stop when EOF
                        break
                    compressed_data += compressor_new.compress(f_data)
                compressed_data += compressor_new.flush()
                s.sendall(compressed_data)
                f.close()
                counter += 1  # increment to next file
                print('220 COMPRESSED UPLOAD COMPLETE')
                s.recv(1024)  # wait for confirmation from server to continue

            else:
                while True:
                    f_data = f.read()
                    if f_data == b'':
                        break
                    s.sendall(f_data)
                time.sleep(.1)
                f.close()
                counter += 1
                print('220 UPLOAD COMPLETE')
                s.recv(1024)  # wait for confirmation from server to continue

    else:
        print('210 UPLOAD ABORTED')


def put():
    file_name = s.recv(1024).decode()  # grab file name
    if os.path.isfile(file_name):  # if file exists
        f = open(file_name, 'rb')
        msg = input("Upload file from the following location? [y/n] \n" + str(pwd()) + "\n")
        s.send(msg.encode())

        if msg == 'y' or msg == 'Y':
            if COMPRESS_MODE:  # if compression enabled
                compressor_new = bz2.BZ2Compressor()  # prevent flush() error. refreshes compressor for multiple files
                new_data = b''
                while True:
                    f_data = f.read()
                    if f_data == b'':
                        break
                    new_data += compressor_new.compress(f_data)  # compress
                new_data += compressor_new.flush()
                s.sendall(new_data)
                f.close()

            else:  # no compression or encryption
                while True:
                    f_data = f.read()
                    if f_data == b'':
                        break
                    time.sleep(.1)
                    s.sendall(f_data)
            s.recv(1024).decode()
            f.close()
            print('220 UPLOAD COMPLETE')
        else:
            print('210 UPLOADED ABORTED')
    else:
        print("210 FILE DOESN'T EXIST!\nUPLOAD ABORTED")


def ls():
    files = []  # list to hold file names
    while True:
        data = s.recv(1024).decode()
        if data == 'done':
            break
        files.append(data)  # add file names to list
    for stuff in files:
        print(stuff)  # iterate and print
    print('220 DIRECTORY LISTED')  # confirmation


def main():
    global ENCRYPT_MODE, COMPRESS_MODE

    while True:
        data = s.recv(1024).decode()  # receive message from server

        if data == 'File exists':  # checks for get command
            get()
        elif data == 'Listing':  # confirmation for ls
            ls()
        elif data == 'put':
            put()
        elif data == 'mget':
            mget()
        elif data == 'mput':
            mput()
        elif data == '220 Compression enabled':
            COMPRESS_MODE = True
            print(data)
        elif data == '220 encryption and compress disabled':
            ENCRYPT_MODE = False
            COMPRESS_MODE = False
            print(data)
        elif data == 'User or Password incorrect. Bye.':
            print(data)
            s.close()
            break
        else:
            print(data)  # print message

        data = s.send(input().encode())  # send message to server

        if not data:  # die if no more data
            break

    s.close()  # close connection


if __name__ == '__main__':
    main()
