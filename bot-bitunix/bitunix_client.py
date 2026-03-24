import hashlib
import time
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

class BitunixClient:
    def __init__(self):
        self.api_key    = os.getenv("BITUNIX_API_KEY")
        self.secret_key = os.getenv("BITUNIX_SECRET_KEY")
        self.base_url   = "https://fapi.bitunix.com"
        self.session    = requests.Session()

    def _generate_signature(self, nonce, timestamp, query_params_str="", body_str=""):
        inner  = nonce + timestamp + self.api_key + query_params_str + body_str
        digest = hashlib.sha256(inner.encode('utf-8')).hexdigest()
        sign   = hashlib.sha256((digest + self.secret_key).encode('utf-8')).hexdigest()
        return sign

    def _request(self, method, path, params=None, body=None):
        timestamp = str(int(time.time() * 1000))
        nonce     = os.urandom(16).hex()[:32]

        query_params_sign = ""
        if params:
            query_params_sign = "".join(f"{k}{v}" for k, v in sorted(params.items()))

        body_str = ""
        if body:
            body_str = json.dumps(body, separators=(',', ':'))

        sign = self._generate_signature(nonce, timestamp, query_params_sign, body_str)

        headers = {
            "api-key":      self.api_key,
            "sign":         sign,
            "nonce":        nonce,
            "timestamp":    timestamp,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }

        url = self.base_url + path
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))

        print(f"\n🌐 {method} {url}")

        try:
            if method == "GET":
                res = self.session.get(url, headers=headers, timeout=15)
            else:
                res = self.session.post(url, data=body_str, headers=headers, timeout=15)

            print(f"   HTTP {res.status_code}")

            if res.status_code == 403:
                import re
                m = re.search(r'event_id[:\s]+([a-z0-9]+)', res.text)
                print("   🚫 WAF 403" + (f" — event_id={m.group(1)}" if m else ""))
                return None

            if not res.text.strip():
                print("   ⚠️  Respuesta vacía")
                return None

            data = res.json()
            print(f"   Respuesta: {json.dumps(data)[:300]}")
            return data

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # BALANCE
    # ─────────────────────────────────────────────────────────────────────────

    def obtener_balance_real(self):
        data = self._request("GET", "/api/v1/futures/account", params={"marginCoin": "USDT"})
        if not data:
            return 0.0
        if str(data.get("code")) == "0":
            items = data.get("data", {})
            if isinstance(items, list):
                items = items[0] if items else {}
            available = float(items.get("available", 0))
            print(f"   💰 Balance USDT disponible: {available}")
            return available
        print(f"   ❌ API error — code={data.get('code')} | msg={data.get('msg','')}")
        return 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # ORDEN MERCADO (APERTURA)
    # ─────────────────────────────────────────────────────────────────────────

    def enviar_orden_mercado(self, symbol, side, percentage, leverage=10):
        balance = self.obtener_balance_real()
        if balance <= 0:
            print(f"❌ Sin saldo disponible (balance={balance})")
            return

        symbol_clean = symbol.replace("/", "")

        # Para mercado necesitamos el precio actual para calcular la qty
        # Usamos el endpoint de tickers para obtenerlo
        ticker = self._request("GET", "/api/v1/futures/market/tickers", params={"symbol": symbol_clean})
        if not ticker or str(ticker.get("code")) != "0":
            print("   ❌ No se pudo obtener el precio de mercado")
            return

        raw = ticker.get("data", [])
        items = raw if isinstance(raw, list) else [raw]
        # Buscar el símbolo correcto en la lista, no coger siempre el primero
        ticker_data = next((t for t in items if t.get("symbol") == symbol_clean), None)
        if not ticker_data:
            print(f"   ❌ No se encontró ticker para {symbol_clean}")
            return
        precio_actual = float(ticker_data.get("lastPrice", 0))
        if precio_actual <= 0:
            print("   ❌ Precio de mercado inválido")
            return

        qty = round((balance * percentage * leverage) / precio_actual, 8)

        print(f"\n📤 MARKET {symbol_clean} {side} | Precio actual: {precio_actual} | Qty: {qty} | x{leverage}")
        print(f"   Margen: {balance * percentage:.2f} USDT")

        data = self._request("POST", "/api/v1/futures/trade/place_order", body={
            "symbol":    symbol_clean,
            "side":      side,
            "tradeSide": "OPEN",
            "orderType": "MARKET",
            "qty":       str(qty),
        })

        if data:
            code = str(data.get("code", ""))
            if code == "0":
                print(f"✅ Orden mercado creada — orderId: {data.get('data',{}).get('orderId','N/A')}")
            else:
                print(f"❌ Error orden — code={code} | msg={data.get('msg','')}")

    # ─────────────────────────────────────────────────────────────────────────
    # ORDEN LÍMITE (APERTURA)
    # ─────────────────────────────────────────────────────────────────────────

    def enviar_orden_limite(self, symbol, side, price, percentage, leverage=10):
        balance = self.obtener_balance_real()
        if balance <= 0:
            print(f"❌ Sin saldo disponible (balance={balance})")
            return

        symbol_clean = symbol.replace("/", "")
        qty          = round((balance * percentage * leverage) / price, 8)

        print(f"\n📤 {symbol_clean} {side} | Precio: {price} | Qty: {qty} | x{leverage}")
        print(f"   Margen: {balance * percentage:.2f} USDT")

        data = self._request("POST", "/api/v1/futures/trade/place_order", body={
            "symbol":    symbol_clean,
            "side":      side,
            "tradeSide": "OPEN",
            "orderType": "LIMIT",
            "price":     str(price),
            "qty":       str(qty),
            "effect":    "GTC",
        })

        if data:
            code = str(data.get("code", ""))
            if code == "0":
                print(f"✅ Orden creada — orderId: {data.get('data',{}).get('orderId','N/A')}")
            else:
                print(f"❌ Error orden — code={code} | msg={data.get('msg','')}")

    # ─────────────────────────────────────────────────────────────────────────
    # TAKE PROFIT (CIERRE PARCIAL/TOTAL)
    # ─────────────────────────────────────────────────────────────────────────

    def gestionar_tp(self, symbol, pct, price):
        print(f"\n🎯 TP {symbol} @ {price} ({pct*100:.0f}%)")
        symbol_clean = symbol.replace("/", "")

        # 1. Posición abierta
        pos_data = self._request(
            "GET",
            "/api/v1/futures/position/get_pending_positions",
            params={"symbol": symbol_clean}
        )
        if not pos_data or str(pos_data.get("code")) != "0":
            print("   ❌ No se pudo obtener la posición")
            return

        raw = pos_data.get("data", [])
        positions = raw if isinstance(raw, list) else raw.get("positionList", [])
        if not positions:
            print("   ⚠️  No hay posición abierta para este par")
            return

        pos         = positions[0]
        position_id = pos.get("positionId")
        total_qty   = float(pos.get("qty", 0))
        pos_side    = pos.get("side")           # "BUY" para LONG, "SELL" para SHORT
        close_side  = "SELL" if pos_side == "BUY" else "BUY"

        # 2. Órdenes de cierre ya pendientes — descuentan del total disponible
        ord_data = self._request(
            "GET",
            "/api/v1/futures/trade/get_pending_orders",
            params={"symbol": symbol_clean, "limit": "50"}
        )
        qty_ya_cubierta = 0.0
        if ord_data and str(ord_data.get("code")) == "0":
            raw_orders = ord_data.get("data", {})
            orders = raw_orders.get("orderList", raw_orders) if isinstance(raw_orders, dict) else raw_orders
            for o in orders:
                # Contar solo las órdenes de cierre (lado contrario a la posición)
                if o.get("side") == close_side:
                    qty_ya_cubierta += float(o.get("qty", 0))

        qty_restante = round(total_qty - qty_ya_cubierta, 8)
        close_qty    = round(qty_restante * pct, 8)

        print(f"   Posición total:  {total_qty}")
        print(f"   Ya cubierta con TPs anteriores: {qty_ya_cubierta}")
        print(f"   Restante disponible: {qty_restante}")
        print(f"   Cerrando {pct*100:.0f}% del restante: {close_qty}")

        if close_qty <= 0:
            print("   ⚠️  No hay posición restante disponible para cubrir con este TP")
            return

        data = self._request("POST", "/api/v1/futures/trade/place_order", body={
            "symbol":     symbol_clean,
            "side":       close_side,
            "tradeSide":  "CLOSE",
            "positionId": position_id,
            "orderType":  "LIMIT",
            "price":      str(price),
            "qty":        str(close_qty),
            "effect":     "GTC",
        })

        if data and str(data.get("code")) == "0":
            print(f"✅ TP ejecutado — orderId: {data.get('data',{}).get('orderId','N/A')}")

    # ─────────────────────────────────────────────────────────────────────────
    # MODIFICAR TP (cambiar precio y/o porcentaje de una orden pendiente)
    # ─────────────────────────────────────────────────────────────────────────

    def modificar_tp(self, symbol, precio_viejo, pct_viejo, precio_nuevo, pct_nuevo):
        """
        Busca una orden pendiente de cierre que coincida con precio_viejo y pct_viejo,
        y la modifica con precio_nuevo y pct_nuevo.
        """
        print(f"\n✏️  Modificar TP {symbol}: {precio_viejo} {pct_viejo*100:.0f}% → {precio_nuevo} {pct_nuevo*100:.0f}%")
        symbol_clean = symbol.replace("/", "")

        # 1. Obtener posición abierta para calcular las qtys
        pos_data = self._request(
            "GET",
            "/api/v1/futures/position/get_pending_positions",
            params={"symbol": symbol_clean}
        )
        if not pos_data or str(pos_data.get("code")) != "0":
            print("   ❌ No se pudo obtener la posición")
            return

        raw = pos_data.get("data", [])
        positions = raw if isinstance(raw, list) else raw.get("positionList", [])
        if not positions:
            print("   ⚠️  No hay posición abierta para este par")
            return

        total_qty  = float(positions[0].get("qty", 0))
        qty_vieja  = round(total_qty * pct_viejo, 8)
        qty_nueva  = round(total_qty * pct_nuevo, 8)

        # 2. Buscar la orden pendiente que coincida con precio_viejo
        ord_data = self._request(
            "GET",
            "/api/v1/futures/trade/get_pending_orders",
            params={"symbol": symbol_clean, "limit": "50"}
        )
        if not ord_data or str(ord_data.get("code")) != "0":
            print("   ❌ No se pudo obtener las órdenes pendientes")
            return

        raw_orders = ord_data.get("data", {})
        orders     = raw_orders.get("orderList", raw_orders) if isinstance(raw_orders, dict) else raw_orders

        orden_encontrada = None
        for order in orders:
            precio_orden = float(order.get("price", 0))
            # Buscar solo por precio (±0.1% tolerancia), la qty la tomamos de la orden real
            if abs(precio_orden - precio_viejo) / precio_viejo < 0.001:
                orden_encontrada = order
                break

        if not orden_encontrada:
            print(f"   ⚠️  No se encontró orden pendiente en precio={precio_viejo} qty≈{qty_vieja}")
            print(f"   💡 Órdenes activas encontradas:")
            for o in orders[:5]:
                print(f"      orderId={o.get('orderId')} price={o.get('price')} qty={o.get('qty')} side={o.get('side')}")
            return

        order_id  = orden_encontrada.get("orderId")
        qty_real  = float(orden_encontrada.get("qty", 0))
        # La nueva qty se calcula siempre sobre la posición ACTUAL × nuevo porcentaje
        # Esto funciona correctamente tanto en caso simple como al promediar entradas
        qty_nueva = round(total_qty * pct_nuevo, 8)
        print(f"   ✅ Orden encontrada — orderId={order_id} | precio={orden_encontrada.get('price')} | qty actual={qty_real}")
        print(f"   Nueva qty: posición {total_qty} × {pct_nuevo*100:.0f}% = {qty_nueva}")

        # 3. Modificar la orden
        data = self._request("POST", "/api/v1/futures/trade/modify_order", body={
            "orderId": order_id,
            "price":   str(precio_nuevo),
            "qty":     str(qty_nueva),
        })

        if data and str(data.get("code")) == "0":
            print(f"✅ TP modificado — orderId: {data.get('data',{}).get('orderId','N/A')}")
            print(f"   {precio_viejo} × {pct_viejo*100:.0f}% → {precio_nuevo} × {pct_nuevo*100:.0f}%")
        else:
            print(f"❌ Error al modificar — code={data.get('code') if data else 'N/A'} | msg={data.get('msg','') if data else ''}")