# استدعاء نظام أوبونتو مجهز بالكامل بواجهة رسومية وخاصية noVNC
FROM dorowu/ubuntu-desktop-lxde-vnc:focal

# تحديد أبعاد الشاشة
ENV RESOLUTION=1280x720

# تعيين كلمة السر الخاصة بالدخول للواجهة
ENV VNC_PASSWORD=Youseif

# تعريف المنصة بأن السيرفر يعمل على منفذ الويب الافتراضي
EXPOSE 80
