# 生成线上地址二维码（存到项目根目录，方便用 iPad 扫）
import qrcode, os
url = "https://dew8788.github.io/duoduo-tianzi/"
img = qrcode.make(url)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "填字乐园二维码.png")
img.save(out)
print("saved", out)