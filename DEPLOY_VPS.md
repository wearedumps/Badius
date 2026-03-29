# Despliegue en VPS Linux (bot + whisper local + IA remota)

Este proyecto queda preparado para correr en una VPS Linux usando:
- IA remota via OpenRouter (sin LLM local)
- Whisper local en CPU
- Panel web opcional

## Despliegue rapido en Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y git
sudo mkdir -p /opt
cd /opt
sudo git clone <tu-repo> bottwitch
sudo chown -R $USER:$USER /opt/bottwitch
cd /opt/bottwitch

# Si clonaste desde Windows, limpia CRLF para scripts bash
sed -i 's/\r$//' scripts/linux/*.sh
chmod +x scripts/linux/*.sh

bash scripts/linux/install_vps.sh
cp config.env.example config.env
nano config.env
```

Prueba rapida:

```bash
bash scripts/linux/start_bot.sh
```

## 1) Subir proyecto a la VPS

```bash
git clone <tu-repo> /opt/bottwitch
cd /opt/bottwitch
```

## 2) Instalar dependencias del sistema y Python

```bash
bash scripts/linux/install_vps.sh
```

Si el repositorio viene desde Windows, ejecuta antes:

```bash
sed -i 's/\r$//' scripts/linux/*.sh
chmod +x scripts/linux/*.sh
```

## 3) Configurar entorno

```bash
cp config.env.example config.env
nano config.env
```

Ajustes minimos recomendados en config.env:
- TWITCH_TOKEN
- TWITCH_BOT_NICK
- TWITCH_CHANNEL
- OPENROUTER_API_KEY
- IA_PROVIDER=openrouter
- WEB_UI_HOST=0.0.0.0
- WEB_UI_AUTO_OPEN=0

## 4) Probar arranque manual

```bash
bash scripts/linux/start_bot.sh
```

Si tambien quieres el panel separado:

```bash
bash scripts/linux/start_web_panel.sh
```

## 5) Crear servicios systemd

Copia los servicios y ajusta usuario/ruta si no usas ubuntu y /opt/bottwitch:

```bash
sudo cp deploy/systemd/bottwitch-bot.service /etc/systemd/system/
sudo cp deploy/systemd/bottwitch-web.service /etc/systemd/system/
```

Editar si hace falta:
- User=ubuntu
- WorkingDirectory=/opt/bottwitch
- ExecStart apuntando a tu ruta real

Recargar y habilitar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bottwitch-bot
sudo systemctl start bottwitch-bot

sudo systemctl enable bottwitch-web
sudo systemctl start bottwitch-web
```

## 6) Ver logs y estado

```bash
sudo systemctl status bottwitch-bot --no-pager
sudo journalctl -u bottwitch-bot -f

sudo systemctl status bottwitch-web --no-pager
sudo journalctl -u bottwitch-web -f
```

## 7) Firewall (si expones panel web)

```bash
sudo ufw allow 8787/tcp
sudo ufw status
```

Para mayor seguridad, deja el puerto cerrado y publica el panel detras de Nginx + autenticacion basica o Cloudflare Tunnel.

## Notas importantes

- No subas config.env al repositorio.
- Si algun token ya se expuso, rotalo.
- Whisper local usa CPU. Si hay latencia alta, sube de plan VPS o reduce carga de transcripcion.
