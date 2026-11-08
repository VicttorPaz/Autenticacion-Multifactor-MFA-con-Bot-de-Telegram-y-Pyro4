import hashlib
import hmac
import secrets
import threading
import time
import urllib.parse
import urllib.request

import Pyro4

from excepciones import (CredencialesInvalidas, CodigoExpirado,
                         CodigoIncorrecto, UsuarioBloqueado, ErrorTelegram)

# ---------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------
TOKEN = "PEGA_AQUI_EL_TOKEN_DE_BOTFATHER"
DURACION_CODIGO = 180    # segundos que vive un código (3 minutos)
MAX_INTENTOS = 3         # fallos permitidos antes de bloquear
TIEMPO_BLOQUEO = 300     # segundos de bloqueo (5 minutos)


def sha(texto):
    # Las contraseñas no se guardan en texto plano, solo su hash SHA-256
    return hashlib.sha256(texto.encode()).hexdigest()


# usuario -> hash de la contraseña y chat_id de Telegram donde llega el código
USUARIOS = {
    "victor": {"password": sha("1234"), "chat_id": 8111995572},
    "gabriela": {"password": sha("1234"), "chat_id": 6525659486},
    "sebastian": {"password": sha("sebastian.1")}   # todavía sin chat_id
}

# ---------------------------------------------------------------
# Estado en memoria (se borra si se reinicia el servidor)
# ---------------------------------------------------------------
codigos = {}        # usuario -> {"codigo", "expira", "fallos"}
fallos_login = {}   # usuario -> contraseñas incorrectas seguidas
bloqueados = {}     # usuario -> momento en que termina su bloqueo
candado = threading.Lock()   # Pyro4 atiende cada cliente en un hilo distinto,
                             # el candado evita que se pisen al tocar los diccionarios


def enviar_telegram(chat_id, texto):
    # Manda el mensaje con la API del bot (sendMessage)
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    datos = urllib.parse.urlencode({"chat_id": chat_id, "text": texto}).encode()
    try:
        urllib.request.urlopen(url, datos, timeout=30)
    except Exception as e:
        raise ErrorTelegram("No se pudo enviar el mensaje a Telegram: " + str(e))


def bloquear(usuario):
    # Marca cuándo termina el bloqueo y limpia el estado pendiente del usuario
    bloqueados[usuario] = time.time() + TIEMPO_BLOQUEO
    fallos_login.pop(usuario, None)
    codigos.pop(usuario, None)


def revisar_bloqueo(usuario):
    # Si el usuario sigue bloqueado lanza la excepción, si ya pasó el tiempo lo libera
    if usuario in bloqueados:
        restante = bloqueados[usuario] - time.time()
        if restante > 0:
            raise UsuarioBloqueado("Cuenta bloqueada, intenta de nuevo en "
                                   + str(int(restante)) + " segundos")
        del bloqueados[usuario]


@Pyro4.expose
class ServicioAuth(object):

    def iniciar_sesion(self, usuario, password):
        # Paso 1: valida usuario y contraseña y manda el código por Telegram
        with candado:
            revisar_bloqueo(usuario)
            datos = USUARIOS.get(usuario)

            # Usuario inexistente o contraseña incorrecta: cuenta como fallo
            if datos is None or not hmac.compare_digest(datos["password"], sha(password)):
                fallos_login[usuario] = fallos_login.get(usuario, 0) + 1
                if fallos_login[usuario] >= MAX_INTENTOS:
                    bloquear(usuario)
                    raise UsuarioBloqueado("Demasiados intentos, cuenta bloqueada "
                                           + str(TIEMPO_BLOQUEO) + " segundos")
                raise CredencialesInvalidas("Usuario o contraseña incorrectos")

            # Credenciales bien pero sin chat_id: no hay a dónde mandar el código
            if "chat_id" not in datos:
                raise ErrorTelegram("Este usuario no tiene un chat_id de Telegram registrado")

            fallos_login.pop(usuario, None)

            # Código de 6 dígitos; zfill rellena con ceros a la izquierda (ej. 004821)
            codigo = str(secrets.randbelow(1000000)).zfill(6)
            enviar_telegram(datos["chat_id"],
                            "Tu código de verificación es " + codigo
                            + ". Vence en " + str(DURACION_CODIGO) + " segundos.")

            # Guarda el código con su hora de vencimiento. Los fallos se conservan
            # si ya había un código activo, así no se evita el límite iniciando sesión de nuevo
            codigos[usuario] = {"codigo": codigo,
                                "expira": time.time() + DURACION_CODIGO,
                                "fallos": codigos.get(usuario, {}).get("fallos", 0)}
            return "Te enviamos un código a tu cuenta de Telegram"

    def verificar_codigo_mfa(self, usuario, codigo):
        # Paso 2: comprueba el código que escribió el usuario
        with candado:
            revisar_bloqueo(usuario)
            activo = codigos.get(usuario)

            # No hay código guardado o ya se venció
            if activo is None:
                raise CodigoExpirado("No hay un código activo, inicia sesión de nuevo")
            if time.time() > activo["expira"]:
                del codigos[usuario]
                raise CodigoExpirado("El código expiró, inicia sesión de nuevo")

            # Código equivocado: suma un fallo y bloquea si llega al límite
            if not hmac.compare_digest(activo["codigo"].encode(), str(codigo).strip().encode()):
                activo["fallos"] += 1
                if activo["fallos"] >= MAX_INTENTOS:
                    bloquear(usuario)
                    raise UsuarioBloqueado("Demasiados códigos incorrectos, cuenta bloqueada "
                                           + str(TIEMPO_BLOQUEO) + " segundos")
                quedan = MAX_INTENTOS - activo["fallos"]
                raise CodigoIncorrecto("Código incorrecto, te quedan " + str(quedan) + " intentos")

            # Código correcto: se borra para que no se pueda usar otra vez
            del codigos[usuario]
            return True


# ---------------------------------------------------------------
# Arranque del servidor Pyro4 (una sola computadora)
# ---------------------------------------------------------------
daemon = Pyro4.Daemon()
ns = Pyro4.locateNS()                       # necesita el name server corriendo
uri = daemon.register(ServicioAuth)
ns.register("mfa.autenticacion", uri)       # nombre con el que lo busca el cliente
print("Servidor MFA listo:", uri)
daemon.requestLoop()
