from queue import Queue
import time
import serial
import threading
import serial.tools.list_ports

from enum import Enum


class ConnStatus(Enum):
    CLOSED = 0
    CONNECTED = 1
    LOSE = 2
    CONNECTING = 3


class SerialData:

    def __init__(self, data_flags):
        self._data_flags = data_flags
        self._serial_status = ConnStatus.LOSE
        self._data_flag_initial = {flag: False for flag in self._data_flags}
        self._queues = {flag: Queue(maxsize=0) for flag in self._data_flags}

        # 初始化展示数据
        self._data_size = 120
        self._data = {flag: [0] * self._data_size for flag in self._data_flags}

        # serial_init
        self.com = serial.Serial()
        self.com.port = "/dev/cu.usbserial-14130"
        self.com.baudrate = 112500
        self.com.timeout = 0.5

    def open_serial(self):
        print("open serial \nport:", self.com.port)
        print("baudrate:", self.com.baudrate)

        try:
            self.com.open()
        except Exception as e:
            print("open serial error:", e)
            return False
        self._serial_status = ConnStatus.CONNECTED

        try:
            self.serial_thread = threading.Thread(target=self.serial_read)
            self.serial_thread.setDaemon(True)
            self.serial_thread.start()
        except Exception as e:
            print("serial thread error:", e)
            return False

        return True

    def close_serial(self):
        try:
            self._serial_status = ConnStatus.CLOSED
            if self.serial_thread.is_alive():
                print("close_serial join")
                self.serial_thread.join()
        except Exception as e:
            print("serial thread join error:", e)
            return False

        self.com.close()
        print("serial com is closed:")
        return True

    def serial_read(self):
        ret = b""
        is_data_coming = False
        while self._serial_status == ConnStatus.CONNECTED:
            n = self.com.inWaiting()
            if n:
                try:
                    ret = self.com.readline()
                except Exception as e:
                    print("readline error:", e)
                is_data_coming = True
                # print(ret)
                if len(ret):
                    try:
                        data_get = ret.decode("UTF-8")
                    except Exception as e:
                        print("decode error:", e)
                        continue
                    data = self.parse_line(data_get)
                    if data is None:
                        print("parse error, data is %s" % data_get)
                    else:
                        flag, item = data
                        if flag in self._data_flags:
                            self._queues[flag].put(item)
            else:
                if not is_data_coming:
                    print("waiting data")
                    time.sleep(1)

    def parse_line(self, data):
        if not data.startswith("$"):
            return None
        items = data[1:-2].split(":")
        if len(items) != 2:
            print("fields num is not right")
            return None
        try:
            flag = items[0]
            item = float(items[1])
        except Exception as e:
            print("format error", e)
            return None
        return flag, item

    def spread_data(self, arr, val):
        for i in range(len(arr)):
            arr[i] = val

    def update_data(self):
        for flag in self._data_flags:
            if self._queues[flag].empty():
                continue
            new_item = self._queues[flag].get()
            self._data[flag] = self._data[flag][1:] + [new_item]
            if not self._data_flag_initial[flag]:
                self.spread_data(self._data[flag], new_item)
                self._data_flag_initial[flag] = True

    def reset_data(self):
        for flag in self._data_flags:
            self._data[flag] = [0] * self._data_size
            self._data_flag_initial[flag] = False

    def detect_serial_port(self):  # 检测串口
        items = []
        while 1:  # 循环检测串口
            port_list = list(serial.tools.list_ports.comports())
            if len(port_list) > 0:
                for p in port_list:
                    show_str = "{} {} - {}".format(p.device, p.name, p.description)
                    if p.manufacturer:
                        show_str += " - {}".format(p.manufacturer)
                    if p.pid:
                        show_str += " - pid(0x{:04X})".format(p.pid)
                    if p.vid:
                        show_str += " - vid(0x{:04X})".format(p.vid)
                    if p.serial_number:
                        show_str += " - v{}".format(p.serial_number)
                    if p.device.startswith("/dev/cu.Bluetooth-Incoming-Port"):
                        continue
                    items.append(show_str)
                break
            time.sleep(0.5)
        return items
