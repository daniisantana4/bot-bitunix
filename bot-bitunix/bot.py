import discord
import os
import re
from dotenv import load_dotenv
from bitunix_client import BitunixClient

load_dotenv()

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bitunix = BitunixClient()

    async def on_ready(self):
        print(f'\n✅ BOT ONLINE: {self.user}')
        print(f'📡 ESCUCHANDO CANAL: {os.getenv("CHANNEL_ID")}\n')

    async def on_message(self, message):
        # 1. Filtro de ID de canal
        target_id = os.getenv("CHANNEL_ID").strip()
        if str(message.channel.id) != target_id:
            return

        # 2. Ignorar si es un mensaje del sistema o vacío
        if not message.content:
            return

        # 3. Limpieza básica para procesar
        # No pasamos a .upper() aquí para que el log se vea real, 
        # pero los buscadores serán insensibles a mayúsculas.
        content = message.content.replace(",", "")
        
        # 4. Detectar intención
        if "LONG" in content.upper() or "SHORT" in content.upper():
            print(f"🚀 SEÑAL DETECTADA: {content}")
            self.procesar_apertura(content)
        elif "TP" in content.upper():
            print(f"🎯 TP DETECTADO: {content}")
            self.procesar_tp(content)

    def procesar_apertura(self, texto):
        try:
            # Buscar el Par (Ej: BTC/USDT)
            par_match = re.search(r"([A-Z]+/[A-Z]+)", texto, re.IGNORECASE)
            par = par_match.group(1).upper() if par_match else None
            
            # Buscar el Precio (Busca 'Precio:', 'precio:', 'PRECIO:' seguido de número)
            price_match = re.search(r"precio:\s*(\d+\.?\d*)", texto, re.IGNORECASE)
            precio = float(price_match.group(1)) if price_match else None
            
            # Buscar la Cantidad (Busca 'Cantidad:', 'cantidad:', 'CANTIDAD:' seguido de número y %)
            qty_match = re.search(r"cantidad:\s*(\d+)%", texto, re.IGNORECASE)
            porcentaje = float(qty_match.group(1)) / 100 if qty_match else None
            
            lado = "BUY" if "LONG" in texto.upper() else "SELL"

            if not par or not porcentaje:
                print("❌ No se pudo extraer el PAR o la CANTIDAD.")
                return

            if "MARKET" in texto.upper() or "MERCADO" in texto.upper():
                print(f"⚡ Enviando orden a MERCADO para {par}")
                self.bitunix.enviar_orden_mercado(par, lado, porcentaje)
            elif precio:
                print(f"🕒 Enviando orden LÍMITE para {par} a {precio}")
                self.bitunix.enviar_orden_limite(par, lado, precio, porcentaje)
            else:
                print("❌ Es una orden límite pero no encontré el precio.")

        except Exception as e:
            print(f"❌ Error crítico procesando apertura: {e}")

    def procesar_tp(self, texto):
        try:
            par_match = re.search(r"([A-Z]+/[A-Z]+)", texto, re.IGNORECASE)
            par = par_match.group(1).upper()
            
            pct_match = re.search(r"(\d+)%", texto)
            porcentaje = float(pct_match.group(1)) / 100
            
            # Busca el precio después de 'en', '@' o 'precio'
            price_match = re.search(r"(?:en|@|precio:)\s*(\d+\.?\d*)", texto, re.IGNORECASE)
            precio_tp = float(price_match.group(1))
            
            self.bitunix.gestionar_tp(par, porcentaje, precio_tp)
        except Exception as e:
            print(f"❌ Error procesando TP: {e}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    client = MyClient()
    client.run(token)
