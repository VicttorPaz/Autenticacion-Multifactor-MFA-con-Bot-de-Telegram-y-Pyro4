import getpass

import Pyro4

from excepciones import (CredencialesInvalidas, CodigoExpirado,
                         CodigoIncorrecto, UsuarioBloqueado, ErrorTelegram)

# Para que Pyro4 reconstruya las excepciones propias en el cliente.
# Sin esto, el cliente recibiría una excepción genérica en vez de la nuestra.
for clase in (CredencialesInvalidas, CodigoExpirado, CodigoIncorrecto,
              UsuarioBloqueado, ErrorTelegram):
    Pyro4.util.SerializerBase.register_dict_to_class(
        "excepciones." + clase.__name__,
        lambda nombre, d, clase=clase: clase(*d.get("args", [])))

# Busca el servicio por nombre en el name server
servicio = Pyro4.Proxy("PYRONAME:mfa.autenticacion")

usuario = input("Usuario: ")
password = getpass.getpass("Contraseña: ")   # getpass no muestra lo que se escribe

try:
    # Paso 1: usuario y contraseña. Si son correctos, el servidor manda el código a Telegram
    print(servicio.iniciar_sesion(usuario, password))

    # Paso 2: pide el código hasta acertar. Los fallos los cuenta el servidor,
    # que al llegar al límite lanza UsuarioBloqueado y se sale del bucle
    autorizado = False
    while not autorizado:
        codigo = input("Código recibido en Telegram: ")
        try:
            autorizado = servicio.verificar_codigo_mfa(usuario, codigo)
        except CodigoIncorrecto as e:
            print("Código incorrecto:", e)
    print("Acceso autorizado, bienvenido", usuario)

# Errores que el servidor avisa con nuestras excepciones
except CredencialesInvalidas as e:
    print("Error de credenciales:", e)
except CodigoExpirado as e:
    print("Código expirado:", e)
except UsuarioBloqueado as e:
    print("Bloqueado:", e)
except ErrorTelegram as e:
    print("Problema con Telegram:", e)
