# Autenticación multifactor con Pyro4 y Telegram

Servicio de inicio de sesión en dos pasos. El usuario escribe su contraseña, el servidor le manda un código de 6 dígitos por Telegram y el acceso se autoriza solo cuando el usuario escribe ese código a tiempo.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)
![Pyro4](https://img.shields.io/badge/Pyro4-objetos%20remotos-informational?style=for-the-badge)
![Name Server](https://img.shields.io/badge/Pyro4-Name%20Server-informational?style=for-the-badge)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![MFA](https://img.shields.io/badge/autenticaci%C3%B3n-multifactor%20(OTP)-orange?style=for-the-badge)
![SHA-256](https://img.shields.io/badge/contrase%C3%B1as-hash%20SHA--256-orange?style=for-the-badge)
![Hilos](https://img.shields.io/badge/concurrencia-hilos%20con%20Lock-informational?style=for-the-badge)
![Arquitectura](https://img.shields.io/badge/arquitectura-cliente--servidor-green?style=for-the-badge)
![RPC](https://img.shields.io/badge/comunicaci%C3%B3n-llamadas%20remotas-green?style=for-the-badge)
![Interfaz](https://img.shields.io/badge/interfaz-consola-lightgrey?style=for-the-badge)

## Tabla de contenido

- [Descripción general](#descripción-general)
- [Características](#características)
- [Requisitos previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración del bot de Telegram](#configuración-del-bot-de-telegram)
- [Configuración del servidor](#configuración-del-servidor)
- [Uso](#uso)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Cómo funciona](#cómo-funciona)
- [Capturas de pantalla](#capturas-de-pantalla)

## Descripción general

Este proyecto es una práctica avanzada de sistemas distribuidos que combina llamadas a métodos remotos con un segundo factor de autenticación. Un servidor Pyro4 guarda los usuarios y sus contraseñas, y un cliente de consola inicia la sesión en dos pasos.

En el primer paso, el cliente envía usuario y contraseña. Si son correctos, el servidor genera un código de 6 dígitos y lo manda al chat de Telegram del usuario mediante un bot. En el segundo paso, el cliente pide ese código y lo envía al servidor, que lo compara y decide si autoriza el acceso. El código dura 3 minutos, se puede usar una sola vez y tras 3 fallos seguidos la cuenta se bloquea durante 5 minutos.

Para que el cliente encuentre al servidor sin conocer su dirección, ambos usan el Name Server de Pyro4, donde el servicio queda publicado como `mfa.autenticacion`. Los errores del servidor viajan hasta el cliente como excepciones propias definidas en `excepciones.py`.

## Características

- Inicio de sesión en dos pasos: contraseña y código recibido por Telegram.
- Código de 6 dígitos generado con el módulo `secrets` y rellenado con ceros a la izquierda cuando hace falta, por ejemplo `004821`.
- El código vence a los 180 segundos y se borra después de usarse con éxito.
- Bloqueo de la cuenta durante 300 segundos tras 3 contraseñas incorrectas seguidas o 3 códigos incorrectos.
- Los fallos de código se conservan si el usuario vuelve a iniciar sesión mientras el código sigue activo, así que reiniciar el proceso no reinicia el contador.
- Las contraseñas se guardan como hash SHA-256 y se comparan con `hmac.compare_digest`.
- El cliente usa `getpass`, por lo que la contraseña no se muestra al escribirla.
- Cinco excepciones propias: `CredencialesInvalidas`, `CodigoExpirado`, `CodigoIncorrecto`, `UsuarioBloqueado` y `ErrorTelegram`.
- Un `threading.Lock` protege los diccionarios compartidos, porque Pyro4 atiende a cada cliente en un hilo distinto.

## Requisitos previos

- Python 3 [COMPLETAR: versión exacta usada]
- pip
- Pyro4
- Una cuenta de Telegram para crear el bot y recibir los códigos
- Conexión a internet en el equipo del servidor, porque envía los mensajes a la API de Telegram

Solo Pyro4 se instala con pip. El resto de los módulos (`hashlib`, `hmac`, `secrets`, `threading`, `time`, `urllib`, `getpass`) vienen con Python.

## Instalación

Guarda `servidor.py`, `cliente.py` y `excepciones.py` en una misma carpeta y abre una terminal dentro de ella. Los tres archivos deben estar juntos, porque el servidor y el cliente importan las excepciones desde `excepciones.py`.

Instala Pyro4:

```bash
pip install Pyro4
```

Si prefieres aislar las dependencias en un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install Pyro4
```

## Configuración del bot de Telegram

El servidor necesita el token de un bot y el `chat_id` de cada usuario.

1. En Telegram, abre una conversación con `@BotFather` y envía `/newbot`. Sigue las instrucciones y copia el token que te entrega.
2. Abre el bot que creaste y presiona Iniciar (`/start`). Un bot no puede escribirle a un usuario que antes no lo ha activado.
3. Escribe cualquier mensaje al bot y abre en el navegador esta dirección, cambiando `TU_TOKEN` por el token real:

   ```text
   https://api.telegram.org/botTU_TOKEN/getUpdates
   ```

4. En la respuesta busca `"chat":{"id":...}`. Ese número es el `chat_id` del usuario.

Repite los pasos 2 a 4 con cada persona que vaya a usar el sistema.

## Configuración del servidor

Antes de iniciar el servidor, edita la parte de configuración de `servidor.py`.

| Variable | Valor en el código | Para qué sirve |
|---|---|---|
| `TOKEN` | `"PEGA_AQUI_EL_TOKEN_DE_BOTFATHER"` | Token del bot de Telegram. Reemplázalo por el tuyo |
| `DURACION_CODIGO` | `180` | Segundos que vive un código |
| `MAX_INTENTOS` | `3` | Fallos permitidos antes de bloquear |
| `TIEMPO_BLOQUEO` | `300` | Segundos que dura el bloqueo |

Los usuarios están en el diccionario `USUARIOS`. Cada uno lleva el hash de su contraseña y el `chat_id` de Telegram donde llegan sus códigos:

```python
USUARIOS = {
    "victor": {"password": sha("[COMPLETAR]"), "chat_id": [COMPLETAR]},
    "gabriela": {"password": sha("[COMPLETAR]"), "chat_id": [COMPLETAR]},
    "sebastian": {"password": sha("[COMPLETAR]")}   # sin chat_id todavía
}
```

Un usuario sin `chat_id` puede escribir bien su contraseña, pero no recibe código y el cliente muestra un error de Telegram.

## Uso

Se necesitan al menos tres terminales abiertas. El orden importa: primero el Name Server, después el servidor y al final el cliente.

### 1. Iniciar el Name Server

```bash
python -m Pyro4.naming
```

Salida esperada:

```text
Not starting broadcast server for localhost.
NS running on localhost:9090 (127.0.0.1)
Warning: HMAC key not set. Anyone can connect to this server!
URI = PYRO:Pyro.NameServer@localhost:9090
```

Deja esta terminal abierta mientras uses el sistema.

### 2. Iniciar el servidor

```bash
python servidor.py
```

Salida esperada:

```text
Servidor MFA listo: PYRO:obj_3f2a9c1e5b7d4e6f8a0b1c2d3e4f5a6b@localhost:51234
```

La URI cambia en cada ejecución. El servidor queda esperando peticiones y tampoco debes cerrar esta terminal.

### 3. Ejecutar el cliente

```bash
python cliente.py
```

Ejemplo de un inicio de sesión correcto. La contraseña no se ve en pantalla porque `getpass` no la muestra:

```text
Usuario: victor
Contraseña:
Te enviamos un código a tu cuenta de Telegram
Código recibido en Telegram: 482913
Acceso autorizado, bienvenido victor
```

El mensaje que llega al chat de Telegram tiene este formato:

```text
Tu código de verificación es 482913. Vence en 180 segundos.
```

Ejemplo con un código incorrecto. El cliente vuelve a pedirlo hasta que se acierte o la cuenta se bloquee:

```text
Código recibido en Telegram: 111111
Código incorrecto: Código incorrecto, te quedan 2 intentos
Código recibido en Telegram: 482913
Acceso autorizado, bienvenido victor
```

Ejemplo con tres códigos incorrectos:

```text
Código recibido en Telegram: 111111
Código incorrecto: Código incorrecto, te quedan 2 intentos
Código recibido en Telegram: 222222
Código incorrecto: Código incorrecto, te quedan 1 intentos
Código recibido en Telegram: 333333
Bloqueado: Demasiados códigos incorrectos, cuenta bloqueada 300 segundos
```

Ejemplo con una contraseña incorrecta:

```text
Usuario: victor
Contraseña:
Error de credenciales: Usuario o contraseña incorrectos
```

Ejemplo de un intento mientras la cuenta está bloqueada:

```text
Usuario: victor
Contraseña:
Bloqueado: Cuenta bloqueada, intenta de nuevo en 287 segundos
```

Ejemplo de un código que se venció:

```text
Código recibido en Telegram: 482913
Código expirado: El código expiró, inicia sesión de nuevo
```

Ejemplo con un usuario que no tiene `chat_id`:

```text
Usuario: sebastian
Contraseña:
Problema con Telegram: Este usuario no tiene un chat_id de Telegram registrado
```

Después de cualquier error distinto de un código incorrecto, el cliente termina y hay que ejecutarlo de nuevo.

### Errores comunes

| Mensaje | Causa probable | Solución |
|---|---|---|
| `Failed to locate the nameserver` | El Name Server no está corriendo | Ejecuta `python -m Pyro4.naming` en otra terminal antes de iniciar el servidor y el cliente |
| `unknown name: mfa.autenticacion` | El servidor no está registrado | Inicia `servidor.py` y espera el mensaje "Servidor MFA listo" |
| `Problema con Telegram: No se pudo enviar el mensaje a Telegram` | Token incorrecto, sin internet, o el usuario nunca presionó Iniciar en el bot | Revisa el token, la conexión del equipo del servidor y que el usuario haya activado el bot |
| `ModuleNotFoundError: No module named 'excepciones'` | Falta `excepciones.py` junto a los otros archivos | Guarda los tres archivos en la misma carpeta |
| `ModuleNotFoundError: No module named 'Pyro4'` | Pyro4 no está instalado | Ejecuta `pip install Pyro4` |

## Estructura del proyecto

```text
.
├── servidor.py       # Servicio de autenticación, envío por Telegram, expiración y bloqueo
├── cliente.py        # Pide usuario, contraseña y código, y muestra el resultado
├── excepciones.py    # Las cinco excepciones propias compartidas por servidor y cliente
```



## Cómo funciona

El proyecto usa Pyro4 (Python Remote Objects), una biblioteca que permite llamar métodos de un objeto que vive en otro proceso, o incluso en otro equipo, como si fuera local. Hay cuatro piezas:

1. Name Server. Es un directorio que relaciona nombres con direcciones de objetos remotos. Se inicia con `python -m Pyro4.naming` y escucha por defecto en el puerto 9090.
2. Servidor (`servidor.py`). Define la clase `ServicioAuth`, marcada con `@Pyro4.expose`. Después de la clase, el script crea un `Pyro4.Daemon`, localiza el Name Server, registra la clase y publica la URI con el nombre `mfa.autenticacion`. Al final, `daemon.requestLoop()` deja el proceso atendiendo llamadas. El estado vive en tres diccionarios: `codigos` guarda el código activo de cada usuario con su hora de vencimiento y sus fallos, `fallos_login` cuenta las contraseñas incorrectas seguidas y `bloqueados` guarda cuándo termina el bloqueo de cada usuario.
3. Cliente (`cliente.py`). Crea un `Pyro4.Proxy("PYRONAME:mfa.autenticacion")`, un objeto intermediario que consulta al Name Server la dirección real y reenvía cada llamada al servidor. Pide el usuario y la contraseña, llama a `iniciar_sesion` y luego pide el código en un ciclo que llama a `verificar_codigo_mfa` hasta que el servidor lo acepte o lance una excepción que lo detenga.
4. Excepciones (`excepciones.py`). El servidor lanza sus propias excepciones y Pyro4 las envía al cliente. Para que el cliente las reconstruya como la clase original y no como una excepción genérica, `cliente.py` registra cada una con `Pyro4.util.SerializerBase.register_dict_to_class`.

Métodos que expone el servicio:

| Método | Qué hace | Devuelve |
|---|---|---|
| `iniciar_sesion(usuario, password)` | Revisa si la cuenta está bloqueada, valida la contraseña, genera el código, lo envía por Telegram y lo guarda con su vencimiento | Texto que avisa que se envió el código |
| `verificar_codigo_mfa(usuario, codigo)` | Revisa el bloqueo, comprueba que el código exista y no haya vencido, lo compara con el que escribió el usuario y lo borra si es correcto | `True` cuando el código es correcto |

Excepciones que puede lanzar cada método:

| Excepción | Cuándo se lanza | Método |
|---|---|---|
| `CredencialesInvalidas` | Usuario inexistente o contraseña incorrecta | `iniciar_sesion` |
| `ErrorTelegram` | Falló el envío a Telegram o el usuario no tiene `chat_id` | `iniciar_sesion` |
| `CodigoIncorrecto` | El código no coincide y todavía quedan intentos | `verificar_codigo_mfa` |
| `CodigoExpirado` | No hay código activo o ya pasaron los 180 segundos | `verificar_codigo_mfa` |
| `UsuarioBloqueado` | Se llegó al máximo de fallos, o la cuenta sigue bloqueada | Ambos |

Flujo de un inicio de sesión:

```text
cliente.py  ->  Name Server: "¿dónde está mfa.autenticacion?"
Name Server ->  cliente.py:  URI del objeto en el servidor
cliente.py  ->  servidor.py: iniciar_sesion("victor", contraseña)
servidor.py ->  Telegram:    código de 6 dígitos al chat del usuario
servidor.py ->  cliente.py:  "Te enviamos un código a tu cuenta de Telegram"
cliente.py  ->  servidor.py: verificar_codigo_mfa("victor", "482913")
servidor.py ->  cliente.py:  True
```

## Capturas de pantalla



Name Server y servidor en ejecución:

<img width="1043" height="151" alt="imagen" src="https://github.com/user-attachments/assets/ff3aabbe-1cf3-4971-886e-9f538d19a28f" />


Cliente pidiendo el código y recibiendo el acceso:

<img width="764" height="153" alt="WhatsApp Image 2026-11-07 at 7 52 14 PM" src="https://github.com/user-attachments/assets/8166eb47-689e-44bb-bbc6-560a9aac475a" />


Mensaje con el código en Telegram:

<img width="721" height="606" alt="imagen" src="https://github.com/user-attachments/assets/23bbc043-9e42-425c-a180-3532cb10e59a" />
