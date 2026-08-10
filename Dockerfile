# نظام أوبونتو الأساسي
FROM ubuntu:22.04

# لمنع أي نوافذ تأكيد مزعجة أثناء بناء السيرفر
ENV DEBIAN_FRONTEND=noninteractive

# تثبيت واجهة XFCE الخفيفة، برنامج XRDP للاتصال، وبيئة بايثون
RUN apt-get update && apt-get install -y \
    xfce4 \
    xfce4-terminal \
    xrdp \
    dbus-x11 \
    python3 \
    python3-pip \
    && apt-get clean

# إنشاء مستخدم للاتصال الخارجي (اليوزر: myuser، الباسورد: 123456)
RUN useradd -ms /bin/bash myuser && \
    echo "myuser:123456" | chpasswd

# إعداد الواجهة لتشتغل بمجرد دخولك
RUN echo "xfce4-session" > /home/myuser/.xsession && \
    chown myuser:myuser /home/myuser/.xsession

RUN usermod -a -G ssl-cert xrdp

# فتح بورت الاتصال الخاص بتطبيق الويندوز (3389)
EXPOSE 3389

# تشغيل خدمة الاتصال وإبقائها تعمل
CMD service xrdp start && tail -f /var/log/xrdp-sesman.log
