import discord
import os
import re
import json
from dotenv import load_dotenv
from bitunix_client import BitunixClient

load_dotenv()

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bitunix = BitunixClient()

    async def on_ready(self):
        print(f'\n' + '='*30)
        print(f'✅ SISTEMA INICIADO')
        print(f'👤 Usuario: {self.user}')
        print(f'📡 Canal Objetivo: {os.getenv("CHANNEL_ID")}')
        print('='*30 + '\n')

    async def on_message(self, message):
        # 1. LOG DE SEGURIDAD: Imprime CUALQUIER mensaje que veas
        print(f"\n📩 [EVENTO] Mensaje detectado en canal: {message.channel.id}")
        
        # 2. COMPROBACIÓN DE ID (con limpieza de espacios)
        target_id = os.getenv("CHANNEL_ID").strip()
        
        if str(message.channel.id) != target_id:
            # Si el ID no coincide, nos avisa por consola para ver si el ID está mal
            print(f"⚠️ Ignorado: El mensaje viene del canal {message.channel.id}, pero esperamos el {target_id}")
            return

        # 3. LOG DE CONTENIDO: Ver qué llega exactamente
        print(f"🆔 ID Coincide. Autor: {message.author}")
        print(f"📄 Texto plano: {message.content}")
        
        # 4. DETECCIÓN DE EMBEDS (Cuadros de texto de bots/canales VIP)
        if not message.content and message.embeds:
            print("📦 El mensaje no tiene texto pero contiene EMBEDS (cuadros).")
            for embed in message.embeds:
                print(f"   Contenido del Embed: {embed.description}")
                # Si las señales vienen en Embeds, usamos la descripción como contenido
                content = str(embed.description).upper().replace(",", "")
        else:
            content = message.content.upper().replace(",", "")

        # Ignorar si nosotros mismos escribimos (para evitar bucles)
        if message.author == self.user:
            return

        # 5. PROCESAMIENTO DE SEÑALES
        if "LONG" in content or "SHORT" in content:
            print("🚀 Detectada SEÑAL DE APERTURA. Procesando...")
            self.procesar_apertura(content)
            
        elif "TP" in content and "CAMBIO" not in content:
            print("🎯 Detectada SEÑAL DE TAKE PROFIT. Procesando...")
            self.procesar_tp(content)
            
        elif "CAMBIO TP" in content:
            print("✏️ Detectada MODIFICACIÓN DE TP. Procesando...")
            self.procesar_cambio_tp(content)

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
            print(f"❌ Error analizando apertura: {e}")

    def procesar_tp(self, texto):
        try:
            par        = re.search(r"([A-Z]+/[A-Z]+)", texto).group(1)
            porcentaje = float(re.search(r"(\d+)%", texto).group(1)) / 100
            precio_tp  = float(re.search(r"EN\s*(\d+\.?\d*)", texto).group(1))
            self.bitunix.gestionar_tp(par, porcentaje, precio_tp)
        except Exception as e:
            print(f"❌ Error analizando TP: {e}")

    def procesar_cambio_tp(self, texto):
        try:
            par     = re.search(r"([A-Z]+/[A-Z]+)", texto).group(1)
            bloques = re.findall(r"(\d+\.?\d*)\s+(\d+)%", texto)
            precio_viejo = float(bloques[0][0])
            pct_viejo    = float(bloques[0][1]) / 100
            precio_nuevo = float(bloques[1][0])
            pct_nuevo    = float(bloques[1][1]) / 100
            self.bitunix.modificar_tp(par, precio_viejo, pct_viejo, precio_nuevo, pct_nuevo)
        except Exception as e:
            print(f"❌ Error analizando cambio TP: {e}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Error: No hay DISCORD_TOKEN")
        exit(1)
    
    client = MyClient()
    client.run(token)
