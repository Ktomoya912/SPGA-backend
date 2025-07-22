import spidev
import time

# SPI設定（bus=0, device=0）
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000  # 1.35MHz

# MCP3008から指定CHの値を読み取る関数
def read_adc(channel):
    if not 0 <= channel <= 7:
        raise ValueError("チャンネルは0〜7を指定してください")

    # SPI通信で送る3バイト（MCP3008は10bit ADC）
    cmd = [1, (8 + channel) << 4, 0]
    response = spi.xfer2(cmd)

    # 応答（10bit）を結合してアナログ値に変換
    value = ((response[1] & 3) << 8) + response[2]
    return value

# 繰り返し取得して表示
try:
    while True:
        value = read_adc(0)  # CH0を読む（AOを接続したピン）
        print(f"土壌センサ値（0〜1023）: {value}")
        time.sleep(1)
except KeyboardInterrupt:
    print("終了します")
finally:
    spi.close()
