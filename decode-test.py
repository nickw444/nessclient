from py_ness_232.event import BaseEvent
from py_ness_232.packet import Packet


def main():
    with open('resources/data.txt') as f:
        for line in f.readlines():
            line = line.strip()
            if len(line) == 0:
                continue

            print(line)
            packet = Packet.decode(line.encode('ascii'))
            print(packet)
            event = BaseEvent.decode(packet)
            print(event)

if __name__ == '__main__':
    main()
