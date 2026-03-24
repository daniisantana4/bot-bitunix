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
        print(f'✅ Bot conectado como {self.user}')
        print(f'📡 Escuchando canal: {os.getenv("CHANNEL_ID")}')

    async def on_message(self, message):
        if str(message.channel.id) != os.getenv("CHANNEL_ID"):
            return

        content = message.content.upper().replace(",", "")

        if "CAMBIO TP" in content:
            print("\n--- MODIFICACIÓN DE TP ---")
            self.procesar_cambio_tp(content)
        elif "LONG" in content or "SHORT" in content:
            print("\n--- NUEVA SEÑAL DE APERTURA ---")
            self.procesar_apertura(content)
        elif "TP" in content:
            print("\n--- SEÑAL DE TAKE PROFIT ---")
            self.procesar_tp(content)

    def procesar_apertura(self, texto):
        try:
            par        = re.search(r"([A-Z]+/[A-Z]+)", texto).group(1)
            porcentaje = float(re.search(r"CANTIDAD:\s*(\d+)%", texto).group(1)) / 100
            lado       = "BUY" if "LONG" in texto else "SELL"

            if "MARKET" in texto:
                self.bitunix.enviar_orden_mercado(par, lado, porcentaje)
            else:
                precio = float(re.search(r"PRECIO:\s*(\d+\.?\d*)", texto).group(1))
                self.bitunix.enviar_orden_limite(par, lado, precio, porcentaje)
        except Exception as e:
            print(f"❌ Error procesando apertura: {e}")

    def procesar_tp(self, texto):
        try:
            par        = re.search(r"([A-Z]+/[A-Z]+)", texto).group(1)
            porcentaje = float(re.search(r"(\d+)%", texto).group(1)) / 100
            precio_tp  = float(re.search(r"EN\s*(\d+\.?\d*)", texto).group(1))
            self.bitunix.gestionar_tp(par, porcentaje, precio_tp)
        except Exception as e:
            print(f"❌ Error en TP: {e}")

    def procesar_cambio_tp(self, texto):
        try:
            par     = re.search(r"([A-Z]+/[A-Z]+)", texto).group(1)
            bloques = re.findall(r"(\d+\.?\d*)\s+(\d+)%", texto)

            if len(bloques) < 2:
                print(f"❌ Formato incorrecto. Usa: CAMBIO TP BTC/USDT 71369 25% A 71372 50%")
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
    # DEBUG TEMPORAL — eliminar tras verificar
    if token:
        print(f"🔑 Token cargado: '{token[:10]}...{token[-5:]}' (longitud: {len(token)})")
    else:
        print("❌ DISCORD_TOKEN no encontrado — revisa las variables en Railway")
    client = MyClient()
    client.run(token)
