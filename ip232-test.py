import logging
import socket
from threading import Thread

from py_ness_232.event import BaseEvent
from py_ness_232.packet import Packet, CommandType

log = logging.getLogger(__name__)


def recv_loop(sock: socket.socket):
    while True:
        data = sock.recv(1024)
        data = data.strip()
        try:
            pkt = Packet.decode(data)
            print(pkt)
            event = BaseEvent.decode(pkt)
            print(event)
        except Exception as e:
            log.error("Unabled to decode packet: %s", data, exc_info=True)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('alarm.home', 2401))

    thread = Thread(target=recv_loop, args=(sock,))
    thread.start()

    while True:
        payload = input("Payload: ").strip()
        if len(payload) == 0:
            continue

        pkt = Packet.create(
            command=CommandType.USER_INTERFACE,
            start=0x83,
            address=0x00,
            data=payload.encode('ascii'),
        )
        pkt_data = pkt.encode()
        print("Sending: {}".format(pkt_data))
        sock.send(pkt_data.encode('ascii'))


if __name__ == '__main__':
    main()
