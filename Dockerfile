FROM sergeykutsko86/base_image:latest
USER nobody
RUN sudo mkdir -p /app
WORKDIR /app
COPY requirements.txt .
RUN sudo pip install -r requirements.txt
COPY . .
RUN sudo chown nobody:nogroup /app
EXPOSE 8080 44300