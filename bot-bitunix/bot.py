import discord
import os
import re
from dotenv import load_dotenv
from bitunix_client import BitunixClient

load_dotenv()

class MyClient(discord.Client):
    def __init__(self):
        # discord.py-self no requiere intents
        super().__init__()
        self.bitunix = BitunixClient()

    async def on_ready(self):
        print(f'\n✅ BOT ONLINE: {self.user}')
        print(f'📡 ESCUCHANDO CANAL: {os.getenv("CHANNEL_ID")}\n')

    async def on_message(self, message):
        target_id = os.getenv("CHANNEL_ID").strip()
        if str(message.channel.id) != target_id:
            return
        if not message.content:
            return

        content = message.content.replace(",", "")

        if "LONG" in content.upper() or "SHORT" in content.upper():
            print(f"🚀 SEÑAL DETECTADA: {content}")
            self.procesar_apertura(content)
        elif "TP" in content.upper():
            print(f"🎯 TP DETECTADO: {content}")
            self.procesar_tp(content)
        elif "CAMBIO TP" in content.upper():
            print(f"✏️  CAMBIO TP DETECTADO: {content}")
            self.procesar_cambio_tp(content)

    def procesar_apertura(self, texto):
        try:
            par_match  = re.search(r"([A-Z]+/[A-Z]+)", texto, re.IGNORECASE)
            par        = par_match.group(1).upper() if par_match else None
            qty_match  = re.search(r"cantidad:\s*(\d+)%", texto, re.IGNORECASE)
            porcentaje = float(qty_match.group(1)) / 100 if qty_match else None
            lado       = "BUY" if "LONG" in texto.upper() else "SELL"

            if not par or not porcentaje:
                print("❌ No se pudo extraer el PAR o la CANTIDAD.")
                return

            if "MARKET" in texto.upper() or "MERCADO" in texto.upper():
                print(f"⚡ Enviando orden a MERCADO para {par}")
                self.bitunix.enviar_orden_mercado(par, lado, porcentaje)
            else:
                price_match = re.search(r"precio:\s*(\d+\.?\d*)", texto, re.IGNORECASE)
                precio      = float(price_match.group(1)) if price_match else None
                if precio:
                    print(f"🕒 Enviando orden LÍMITE para {par} a {precio}")
                    self.bitunix.enviar_orden_limite(par, lado, precio, porcentaje)
                else:
                    print("❌ Es una orden límite pero no encontré el precio.")
        except Exception as e:
            print(f"❌ Error procesando apertura: {e}")

    def procesar_tp(self, texto):
        try:
            par_match   = re.search(r"([A-Z]+/[A-Z]+)", texto, re.IGNORECASE)
            par         = par_match.group(1).upper()
            pct_match   = re.search(r"(\d+)%", texto)
            porcentaje  = float(pct_match.group(1)) / 100
            price_match = re.search(r"(?:en|@|precio:)\s*(\d+\.?\d*)", texto, re.IGNORECASE)
            precio_tp   = float(price_match.group(1))
            self.bitunix.gestionar_tp(par, porcentaje, precio_tp)
        except Exception as e:
            print(f"❌ Error procesando TP: {e}")

    def procesar_cambio_tp(self, texto):
        try:
            par_match = re.search(r"([A-Z]+/[A-Z]+)", texto, re.IGNORECASE)
            par       = par_match.group(1).upper()
            bloques   = re.findall(r"(\d+\.?\d*)\s+(\d+)%", texto)

            if len(bloques) < 2:
                print("❌ Formato incorrecto. Usa: CAMBIO TP BTC/USDT 71369 25% A 71372 50%")
                return

            precio_viejo = float(bloques[0][0])
            pct_viejo    = float(bloques[0][1]) / 100
            precio_nuevo = float(bloques[1][0])
            pct_nuevo    = float(bloques[1][1]) / 100

            self.bitunix.modificar_tp(par, precio_viejo, pct_viejo, precio_nuevo, pct_nuevo)
        except Exception as e:
            print(f"❌ Error en cambio TP: {e}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN no encontrado")
        exit(1)
    print(f"🔑 Token cargado (longitud: {len(token)})")
    client = MyClient()
    client.run(token)
