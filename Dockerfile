# استخدام نسخة خفيفة جداً مخصصة لـ Code Server
FROM codercom/code-server:latest

# تحديد مجلد العمل
WORKDIR /home/coder/project

# تثبيت بايثون وأدواته
USER root
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
USER coder

# تعيين كلمة السر (استبدل "Youseif" بالباسورد الذي تريده)
ENV PASSWORD=Youseif

# فتح بورت 8080 وهو البورت الافتراضي لـ Code Server
EXPOSE 8080

# تشغيل المحرر
CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "password", "."]
